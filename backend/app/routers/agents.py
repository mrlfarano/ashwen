import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

from app.database import get_session
from app.models import Agent, Project
from app.schemas import (
    AgentCreate,
    AgentResponse,
    AgentUpdate,
    DeleteResponse,
    InitializeAgentsResponse,
    serialize_agent,
)

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)

# Valid LLM providers
VALID_LLM_PROVIDERS = {"openai", "anthropic", "ollama"}

DEFAULT_AGENTS = {
    "architect": {
        "name": "Architect",
        "persona": "Wise strategist",
        "system_prompt": """You are the Architect. Before any code is written, you analyze requirements, 
evaluate trade-offs, and design systems that balance simplicity with scalability.
You ask clarifying questions. You document decisions with rationale.

Guidelines:
- Start with understanding the problem before proposing solutions
- Consider maintainability, scalability, and complexity trade-offs
- Ask clarifying questions when requirements are ambiguous
- Document your reasoning for major decisions
- Prefer proven patterns over novel ones unless there's clear benefit

Tone: Thoughtful, asks "why" before "how", strategic.""",
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
    },
    "historian": {
        "name": "Historian",
        "persona": "Knowledge keeper",
        "system_prompt": """You are the Historian. You query and retrieve relevant context from 
the project's memory. You surface past decisions, patterns, and learnings when they're relevant.

Guidelines:
- Search memory for relevant context before responding
- Surface past decisions that might inform current discussions
- Track patterns across sessions and remind the team
- Maintain the project's institutional knowledge
- Flag when current decisions conflict with past decisions

Tone: Informed, contextual, reminds the team of relevant history.""",
        "llm_provider": "ollama",
        "llm_model": "qwen3:4b",
    },
    "ui_builder": {
        "name": "UI Builder",
        "persona": "Visual craftsman",
        "system_prompt": """You are the UI Builder. You craft beautiful, responsive, accessible user interfaces.
You write clean frontend code with attention to user experience and visual polish.

Guidelines:
- Write clean, modular frontend code
- Consider accessibility (a11y) in all components
- Ensure responsive design works across devices
- Prefer component-based architecture
- Document component props and usage

Tone: Confident, practical, ships working interfaces.""",
        "llm_provider": "anthropic",
        "llm_model": "claude-3-5-sonnet-20241022",
    },
    "api_builder": {
        "name": "API Builder",
        "persona": "Systems plumber",
        "system_prompt": """You are the API Builder. You design and implement robust backend systems.
You write clean API endpoints, handle databases, and ensure system reliability.

Guidelines:
- Design clear RESTful or GraphQL APIs
- Handle errors gracefully with proper status codes
- Write database queries efficiently and securely
- Consider rate limiting, validation, and edge cases
- Document endpoints with examples

Tone: Methodical, reliable, builds systems that work.""",
        "llm_provider": "anthropic",
        "llm_model": "claude-3-5-sonnet-20241022",
    },
    "ui_reviewer": {
        "name": "UI Reviewer",
        "persona": "Pixel perfectionist",
        "system_prompt": """You are the UI Reviewer. You catch UI/UX issues, accessibility problems,
and performance concerns that others might miss.

Guidelines:
- Check accessibility (ARIA, keyboard nav, contrast)
- Review responsive behavior across breakpoints
- Identify performance issues (bundle size, render cycles)
- Ensure consistent styling and spacing
- Validate user experience flows

Tone: Detail-oriented, constructive, suggests fixes not just problems.""",
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
    },
    "api_reviewer": {
        "name": "API Reviewer",
        "persona": "Security auditor",
        "system_prompt": """You are the API Reviewer. You identify security vulnerabilities, edge cases,
and potential failures in backend systems.

Guidelines:
- Check for SQL injection, XSS, CSRF vulnerabilities
- Review authentication and authorization logic
- Identify unhandled edge cases and error states
- Check input validation and sanitization
- Review rate limiting and abuse prevention

Tone: Thorough, security-conscious, provides specific line-level feedback.""",
        "llm_provider": "openai",
        "llm_model": "gpt-4o",
    },
}


@router.get("/project/{project_id}", response_model=list[AgentResponse])
async def list_agents(project_id: str, session: AsyncSession = Depends(get_session)):
    """
    List all agents for a specific project.
    
    Args:
        project_id: UUID of the project
        
    Returns:
        List[Agent]: All agents for the project, ordered by creation time
        
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 422 if project_id is invalid
        HTTPException: 500 if database query fails
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project ID is required"
        )
    
    try:
        # Verify project exists
        result = await session.execute(select(Project.id).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Get all agents for this project
        result = await session.execute(
            select(Agent)
            .where(Agent.project_id == project_id)
            .order_by(Agent.created_at.asc())
        )
        agents = result.scalars().all()

        logger.info(f"Retrieved {len(agents)} agents for project {project_id}")
        return [serialize_agent(agent) for agent in agents]
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error listing agents for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agents from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing agents for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving agents"
        )


@router.post("/project/{project_id}", status_code=status.HTTP_201_CREATED, response_model=AgentResponse)
async def create_agent(
    project_id: str,
    payload: AgentCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new agent for a project.
    
    Args:
        project_id: UUID of the project
        payload: Agent creation data
        
    Returns:
        Agent: The newly created agent
        
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 422 if validation fails (invalid provider, empty fields)
        HTTPException: 500 if database operation fails
    """
    # Validate project_id
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project ID is required"
        )
    
    # Validate required fields
    if not payload.name or not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent name is required and cannot be empty"
        )
    
    if not payload.persona or not payload.persona.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent persona is required and cannot be empty"
        )
    
    if not payload.system_prompt or not payload.system_prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent system prompt is required and cannot be empty"
        )
    
    # Validate LLM provider
    if payload.llm_provider not in VALID_LLM_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid LLM provider '{payload.llm_provider}'. Must be one of: {', '.join(sorted(VALID_LLM_PROVIDERS))}"
        )
    
    # Validate confidence threshold
    if not 0.0 <= payload.confidence_threshold <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confidence threshold must be between 0.0 and 1.0"
        )
    
    try:
        # Verify project exists
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Create agent
        agent = Agent(
            project_id=project_id,
            name=payload.name.strip(),
            persona=payload.persona.strip(),
            system_prompt=payload.system_prompt.strip(),
            llm_provider=payload.llm_provider,
            llm_model=payload.llm_model,
            llm_config=json.dumps(payload.llm_config or {}),
            proactivity_enabled=payload.proactivity_enabled,
            confidence_threshold=payload.confidence_threshold,
        )
        session.add(agent)
        await session.commit()
        await session.refresh(agent)
        
        logger.info(f"Created agent: {agent.id} - {agent.name} for project {project_id}")
        return serialize_agent(agent)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error creating agent for project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create agent in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating agent for project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the agent"
        )


@router.post("/project/{project_id}/initialize", status_code=status.HTTP_201_CREATED, response_model=InitializeAgentsResponse)
async def initialize_default_agents(project_id: str, session: AsyncSession = Depends(get_session)):
    """
    Initialize a project with default team of agents.
    
    Creates 6 default agents: Architect, Historian, UI Builder, API Builder, UI Reviewer, API Reviewer.
    
    Args:
        project_id: UUID of the project
        
    Returns:
        dict: Number of agents initialized
        
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 400 if project already has agents
        HTTPException: 422 if project_id is invalid
        HTTPException: 500 if database operation fails
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project ID is required"
        )
    
    try:
        # Verify project exists
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Check if project already has agents
        existing_agents = await session.execute(select(Agent.id).where(Agent.project_id == project_id))
        if existing_agents.first():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project '{project.name}' already has agents configured. Delete existing agents first to reinitialize."
            )
        
        # Create default agents
        for key, config in DEFAULT_AGENTS.items():
            agent = Agent(
                project_id=project_id,
                name=config["name"],
                persona=config["persona"],
                system_prompt=config["system_prompt"],
                llm_provider=config["llm_provider"],
                llm_model=config["llm_model"],
            )
            session.add(agent)
        
        await session.commit()
        
        logger.info(f"Initialized {len(DEFAULT_AGENTS)} default agents for project {project_id}")
        return {
            "initialized": len(DEFAULT_AGENTS),
            "project_id": project_id,
            "agents": list(DEFAULT_AGENTS.keys())
        }
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error initializing agents for project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize default agents in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error initializing agents for project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while initializing agents"
        )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    """
    Get a specific agent by ID.
    
    Args:
        agent_id: UUID of the agent
        
    Returns:
        Agent: The requested agent
        
    Raises:
        HTTPException: 404 if agent not found
        HTTPException: 422 if agent_id is invalid
        HTTPException: 500 if database query fails
    """
    if not agent_id or not agent_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent ID is required"
        )
    
    try:
        result = await session.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID '{agent_id}' not found"
            )

        return serialize_agent(agent)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve agent from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the agent"
        )


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    payload: AgentUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Update an agent's configuration.
    
    Args:
        agent_id: UUID of the agent
        payload: Agent update data (partial updates supported)
        
    Returns:
        Agent: The updated agent
        
    Raises:
        HTTPException: 404 if agent not found
        HTTPException: 422 if validation fails (invalid provider, empty fields)
        HTTPException: 500 if database operation fails
    """
    # Validate agent_id
    if not agent_id or not agent_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent ID is required"
        )
    
    # Validate fields if provided
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent name cannot be empty"
        )
    
    if payload.persona is not None and not payload.persona.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent persona cannot be empty"
        )
    
    if payload.system_prompt is not None and not payload.system_prompt.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent system prompt cannot be empty"
        )
    
    if payload.llm_provider is not None and payload.llm_provider not in VALID_LLM_PROVIDERS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid LLM provider '{payload.llm_provider}'. Must be one of: {', '.join(sorted(VALID_LLM_PROVIDERS))}"
        )
    
    if payload.confidence_threshold is not None and not 0.0 <= payload.confidence_threshold <= 1.0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Confidence threshold must be between 0.0 and 1.0"
        )
    
    try:
        result = await session.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID '{agent_id}' not found"
            )
        
        # Apply updates
        if payload.name is not None:
            agent.name = payload.name.strip()
        if payload.persona is not None:
            agent.persona = payload.persona.strip()
        if payload.system_prompt is not None:
            agent.system_prompt = payload.system_prompt.strip()
        if payload.llm_provider is not None:
            agent.llm_provider = payload.llm_provider
        if payload.llm_model is not None:
            agent.llm_model = payload.llm_model
        if payload.llm_config is not None:
            agent.llm_config = json.dumps(payload.llm_config)
        if payload.proactivity_enabled is not None:
            agent.proactivity_enabled = payload.proactivity_enabled
        if payload.confidence_threshold is not None:
            agent.confidence_threshold = payload.confidence_threshold
        
        await session.commit()
        await session.refresh(agent)
        
        logger.info(f"Updated agent: {agent_id} - {agent.name}")
        return serialize_agent(agent)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating agent {agent_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update agent in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating agent {agent_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the agent"
        )


@router.delete("/{agent_id}", status_code=status.HTTP_200_OK, response_model=DeleteResponse)
async def delete_agent(agent_id: str, session: AsyncSession = Depends(get_session)):
    """
    Delete an agent.
    
    Args:
        agent_id: UUID of the agent to delete
        
    Returns:
        dict: Confirmation of deletion
        
    Raises:
        HTTPException: 404 if agent not found
        HTTPException: 422 if agent_id is invalid
        HTTPException: 500 if database operation fails
    """
    if not agent_id or not agent_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Agent ID is required"
        )
    
    try:
        result = await session.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID '{agent_id}' not found"
            )
        
        agent_name = agent.name
        await session.delete(agent)
        await session.commit()
        
        logger.info(f"Deleted agent: {agent_id} - {agent_name}")
        return {"deleted": True, "agent_id": agent_id}
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting agent {agent_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete agent from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting agent {agent_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the agent"
        )
