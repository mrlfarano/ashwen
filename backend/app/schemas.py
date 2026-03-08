import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models import Agent, MemoryEntry, Message, Project


class ProjectCreate(BaseModel):
    name: str
    path: str
    description: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    linked_projects: Optional[list[str]] = None


class AgentCreate(BaseModel):
    name: str
    persona: str
    system_prompt: str
    llm_provider: str = "ollama"
    llm_model: str = "qwen3:4b"
    llm_config: dict[str, Any] = Field(default_factory=dict)
    proactivity_enabled: bool = True
    confidence_threshold: float = 0.75


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    persona: Optional[str] = None
    system_prompt: Optional[str] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    llm_config: Optional[dict[str, Any]] = None
    proactivity_enabled: Optional[bool] = None
    confidence_threshold: Optional[float] = None


class MemoryCreate(BaseModel):
    memory_type: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MemoryUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class CredentialSet(BaseModel):
    api_key: str


class ProjectResponse(BaseModel):
    id: str
    name: str
    path: str
    description: Optional[str] = None
    linked_projects: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AgentResponse(BaseModel):
    id: str
    project_id: str
    name: str
    persona: str
    system_prompt: str
    llm_provider: str
    llm_model: str
    llm_config: dict[str, Any] = Field(default_factory=dict)
    proactivity_enabled: bool
    confidence_threshold: float
    status: str
    created_at: datetime


class MessageResponse(BaseModel):
    id: str
    project_id: str
    agent_id: Optional[str] = None
    role: str
    content: str
    message_type: str
    confidence: Optional[float] = None
    tokens_used: Optional[int] = None
    created_at: datetime


class MemoryEntryResponse(BaseModel):
    id: str
    project_id: str
    memory_type: str
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CredentialStatusResponse(BaseModel):
    provider: str
    configured: bool


class CredentialStoredResponse(BaseModel):
    provider: str
    stored: bool
    action: Optional[str] = None


class DeleteResponse(BaseModel):
    deleted: bool
    project_id: Optional[str] = None
    agent_id: Optional[str] = None
    memory_id: Optional[str] = None


class InitializeAgentsResponse(BaseModel):
    initialized: int
    project_id: str
    agents: list[str]


def _parse_json_field(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def serialize_project(project: Project) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        name=project.name,
        path=project.path,
        description=project.description,
        linked_projects=_parse_json_field(project.linked_projects, []),
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


def serialize_agent(agent: Agent) -> AgentResponse:
    return AgentResponse(
        id=agent.id,
        project_id=agent.project_id,
        name=agent.name,
        persona=agent.persona,
        system_prompt=agent.system_prompt,
        llm_provider=agent.llm_provider,
        llm_model=agent.llm_model,
        llm_config=_parse_json_field(agent.llm_config, {}),
        proactivity_enabled=agent.proactivity_enabled,
        confidence_threshold=agent.confidence_threshold,
        status=agent.status,
        created_at=agent.created_at,
    )


def serialize_message(message: Message) -> MessageResponse:
    return MessageResponse(
        id=message.id,
        project_id=message.project_id,
        agent_id=message.agent_id,
        role=message.role,
        content=message.content,
        message_type=message.message_type,
        confidence=message.confidence,
        tokens_used=message.tokens_used,
        created_at=message.created_at,
    )


def serialize_memory_entry(entry: MemoryEntry) -> MemoryEntryResponse:
    return MemoryEntryResponse(
        id=entry.id,
        project_id=entry.project_id,
        memory_type=entry.memory_type,
        title=entry.title,
        content=entry.content,
        metadata=_parse_json_field(entry.entry_metadata, {}),
        file_path=entry.file_path,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )
