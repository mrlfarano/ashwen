import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.database import get_session
from app.models import Project, Message, Agent, MemoryEntry
from app.schemas import (
    DeleteResponse,
    MessageResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    serialize_message,
    serialize_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])
logger = logging.getLogger(__name__)

# Pattern to detect potentially dangerous path components
DANGEROUS_PATH_PATTERNS = re.compile(r'(\.\.\/|\.\.\\|^\/|^\\|[<>:"|?*])')


def validate_project_path(path: str) -> tuple[bool, str]:
    """
    Validate a project path for safety and existence.
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not path or not path.strip():
        return False, "Project path is required"
    
    path = path.strip()
    
    # Check for dangerous patterns
    if DANGEROUS_PATH_PATTERNS.search(path):
        return False, "Project path contains invalid or potentially unsafe characters"
    
    # Normalize and check if path exists
    try:
        normalized_path = Path(path).resolve()
        if not normalized_path.exists():
            return False, f"Project path does not exist: {path}"
        if not normalized_path.is_dir():
            return False, f"Project path is not a directory: {path}"
    except (OSError, ValueError) as e:
        return False, f"Invalid project path: {str(e)}"
    
    return True, ""


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(session: AsyncSession = Depends(get_session)):
    """
    List all projects ordered by last update time.
    
    Returns:
        List[Project]: All projects in the system
        
    Raises:
        HTTPException: 500 if database query fails
    """
    try:
        result = await session.execute(select(Project).order_by(Project.updated_at.desc()))
        projects = result.scalars().all()
        return [serialize_project(project) for project in projects]
    except SQLAlchemyError as e:
        logger.error(f"Database error listing projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve projects from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error listing projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing projects"
        )


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=ProjectResponse)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new project.
    
    Args:
        payload: Project creation data (name, path, description)
        
    Returns:
        Project: The newly created project
        
    Raises:
        HTTPException: 400 if project path already exists
        HTTPException: 422 if validation fails
        HTTPException: 500 if database operation fails
    """
    # Validate required fields
    if not payload.name or not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project name is required and cannot be empty"
        )
    
    # Validate path
    is_valid, error_msg = validate_project_path(payload.path)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error_msg
        )
    
    normalized_path = str(Path(payload.path.strip()).resolve())
    
    try:
        # Check for existing project with same path
        existing = await session.execute(select(Project).where(Project.path == normalized_path))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with path '{payload.path}' already exists. Please choose a different path."
            )
        
        # Check for existing project with same name (warning, not error)
        name_check = await session.execute(
            select(Project).where(Project.name == payload.name.strip())
        )
        if name_check.scalar_one_or_none():
            logger.warning(f"Creating project with duplicate name: {payload.name}")
        
        # Create new project
        project = Project(
            name=payload.name.strip(),
            path=normalized_path,
            description=payload.description.strip() if payload.description else None,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        
        # Create .ashwen directory for the project
        ashwen_dir = Path(normalized_path) / ".ashwen"
        try:
            ashwen_dir.mkdir(parents=True, exist_ok=True)
            (ashwen_dir / "memory" / "episodic").mkdir(parents=True, exist_ok=True)
            (ashwen_dir / "memory" / "semantic").mkdir(parents=True, exist_ok=True)
            (ashwen_dir / "memory" / "procedural").mkdir(parents=True, exist_ok=True)
            logger.info(f"Created .ashwen directory structure at {ashwen_dir}")
        except OSError as e:
            logger.warning(f"Could not create .ashwen directory: {e}")
        
        logger.info(f"Created project: {project.id} - {project.name}")
        return serialize_project(project)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error creating project: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error creating project: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the project"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, session: AsyncSession = Depends(get_session)):
    """
    Get a specific project by ID.
    
    Args:
        project_id: UUID of the project
        
    Returns:
        Project: The requested project
        
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 422 if project_id is invalid
        HTTPException: 500 if database query fails
    """
    # Validate project_id format
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project ID is required"
        )
    
    try:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        return serialize_project(project)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving the project"
        )


@router.get("/{project_id}/messages", response_model=list[MessageResponse])
async def get_project_messages(project_id: str, session: AsyncSession = Depends(get_session)):
    """
    Load historical messages for a project.
    
    Args:
        project_id: UUID of the project
        
    Returns:
        List[Message]: All messages for the project, ordered chronologically
        
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
        project_result = await session.execute(select(Project).where(Project.id == project_id))
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Get all messages for this project, ordered by creation time
        messages_result = await session.execute(
            select(Message)
            .where(Message.project_id == project_id)
            .order_by(Message.created_at.asc())
        )
        messages = messages_result.scalars().all()

        logger.info(f"Retrieved {len(messages)} messages for project {project_id}")
        return [serialize_message(message) for message in messages]
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error retrieving messages for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error retrieving messages for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving messages"
        )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Update a project's metadata.
    
    Note: Project path cannot be changed after creation.
    
    Args:
        project_id: UUID of the project
        payload: Project update data (partial updates supported)
        
    Returns:
        Project: The updated project
        
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 422 if validation fails
        HTTPException: 500 if database operation fails
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project ID is required"
        )
    
    # Validate fields if provided
    if payload.name is not None and not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project name cannot be empty"
        )
    
    try:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Apply updates
        if payload.name is not None:
            project.name = payload.name.strip()
        if payload.description is not None:
            project.description = payload.description.strip() if payload.description else None
        if payload.linked_projects is not None:
            import json
            project.linked_projects = json.dumps(payload.linked_projects)
        
        await session.commit()
        await session.refresh(project)
        
        logger.info(f"Updated project: {project_id} - {project.name}")
        return serialize_project(project)
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error updating project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project in database"
        )
    except Exception as e:
        logger.error(f"Unexpected error updating project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating the project"
        )


@router.delete("/{project_id}", status_code=status.HTTP_200_OK, response_model=DeleteResponse)
async def delete_project(
    project_id: str,
    cleanup_files: bool = Query(False, description="Also delete .ashwen directory"),
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a project and all associated data.
    
    Args:
        project_id: UUID of the project to delete
        cleanup_files: If True, also delete the .ashwen directory
        
    Returns:
        dict: Confirmation of deletion
        
    Raises:
        HTTPException: 404 if project not found
        HTTPException: 422 if project_id is invalid
        HTTPException: 500 if database operation fails
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project ID is required"
        )
    
    try:
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        project_name = project.name
        project_path = project.path
        
        await session.delete(project)
        await session.commit()
        
        # Optionally clean up .ashwen directory
        if cleanup_files:
            ashwen_dir = Path(project_path) / ".ashwen"
            if ashwen_dir.exists():
                try:
                    shutil.rmtree(ashwen_dir)
                    logger.info(f"Cleaned up .ashwen directory for project {project_id}")
                except OSError as e:
                    logger.warning(f"Could not clean up .ashwen directory: {e}")
        
        logger.info(f"Deleted project: {project_id} - {project_name}")
        return {"deleted": True, "project_id": project_id}
        
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.error(f"Database error deleting project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project from database"
        )
    except Exception as e:
        logger.error(f"Unexpected error deleting project {project_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while deleting the project"
        )


# ============================================================================
# Enhanced Project Stats and Batch Operations
# ============================================================================


class ProjectStatsResponse(BaseModel):
    """Statistics for a project."""
    project_id: str
    project_name: str
    agent_count: int = Field(description="Number of agents in the project")
    message_count: int = Field(description="Total messages in the project")
    memory_count: int = Field(description="Total memory entries")
    last_activity: Optional[str] = Field(None, description="ISO timestamp of last message")
    storage_size_bytes: Optional[int] = Field(None, description="Size of .ashwen directory")


@router.get("/{project_id}/stats", response_model=ProjectStatsResponse)
async def get_project_stats(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get statistics for a project.
    
    Returns counts of agents, messages, memory entries, and storage info.
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Project ID is required"
        )
    
    try:
        # Get project
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Count agents
        agent_count_result = await session.execute(
            select(func.count()).select_from(Agent).where(Agent.project_id == project_id)
        )
        agent_count = agent_count_result.scalar() or 0
        
        # Count messages
        message_count_result = await session.execute(
            select(func.count()).select_from(Message).where(Message.project_id == project_id)
        )
        message_count = message_count_result.scalar() or 0
        
        # Count memory entries
        memory_count_result = await session.execute(
            select(func.count()).select_from(MemoryEntry).where(MemoryEntry.project_id == project_id)
        )
        memory_count = memory_count_result.scalar() or 0
        
        # Get last activity
        last_message_result = await session.execute(
            select(Message)
            .where(Message.project_id == project_id)
            .order_by(Message.created_at.desc())
            .limit(1)
        )
        last_message = last_message_result.scalar_one_or_none()
        last_activity = last_message.created_at.isoformat() if last_message else None
        
        # Calculate storage size
        storage_size = None
        ashwen_dir = Path(project.path) / ".ashwen"
        if ashwen_dir.exists():
            try:
                storage_size = sum(f.stat().st_size for f in ashwen_dir.rglob("*") if f.is_file())
            except OSError:
                pass
        
        return ProjectStatsResponse(
            project_id=project_id,
            project_name=project.name,
            agent_count=agent_count,
            message_count=message_count,
            memory_count=memory_count,
            last_activity=last_activity,
            storage_size_bytes=storage_size,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get project statistics"
        )


@router.get("/recent/list", response_model=list[ProjectResponse])
async def list_recent_projects(
    limit: int = Query(5, ge=1, le=20, description="Number of recent projects"),
    session: AsyncSession = Depends(get_session),
):
    """
    List most recently accessed projects.
    
    This is a convenience endpoint for the UI to show recent projects.
    """
    try:
        result = await session.execute(
            select(Project)
            .order_by(Project.updated_at.desc())
            .limit(limit)
        )
        projects = result.scalars().all()
        return [serialize_project(project) for project in projects]
    except Exception as e:
        logger.error(f"Error listing recent projects: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent projects"
        )


@router.post("/batch/delete", response_model=dict)
async def batch_delete_projects(
    project_ids: list[str],
    session: AsyncSession = Depends(get_session),
):
    """
    Delete multiple projects in a single request.
    
    Args:
        project_ids: List of project UUIDs to delete
        
    Returns:
        dict: Summary of deletion results
    """
    if not project_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No project IDs provided"
        )
    
    if len(project_ids) > 50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Maximum 50 projects can be deleted in a single batch"
        )
    
    deleted = []
    failed = []
    
    for project_id in project_ids:
        try:
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            
            if project:
                await session.delete(project)
                deleted.append(project_id)
            else:
                failed.append({"id": project_id, "reason": "Not found"})
        except Exception as e:
            failed.append({"id": project_id, "reason": str(e)})
    
    try:
        await session.commit()
    except Exception as e:
        logger.error(f"Batch delete commit failed: {e}")
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete batch deletion"
        )
    
    logger.info(f"Batch deleted {len(deleted)} projects, {len(failed)} failed")
    return {
        "deleted_count": len(deleted),
        "failed_count": len(failed),
        "deleted": deleted,
        "failed": failed,
    }


@router.get("/path/{project_path:path}", response_model=ProjectResponse)
async def get_project_by_path(
    project_path: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a project by its filesystem path.
    
    Useful for checking if a directory is already registered as a project.
    """
    try:
        # Normalize the path
        normalized_path = str(Path(project_path).resolve())
        
        result = await session.execute(
            select(Project).where(Project.path == normalized_path)
        )
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No project found at path: {project_path}"
            )
        
        return serialize_project(project)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error finding project by path: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to find project"
        )
