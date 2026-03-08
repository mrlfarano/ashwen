import httpx
import uuid
import logging
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import select, text

from app.config import get_data_dir, get_encryption_key, settings
from app.database import async_session_maker, engine, init_db
from app.models import Agent, Credential, Message, Project
from app.routers import agents, credentials, memory, projects
from app.services.agents.base import AgentBase

# Configure logging for request tracing
logger = logging.getLogger(__name__)

# Configuration constants for request validation
MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB max request size
ALLOWED_CONTENT_TYPES = {
    "application/json",
    "application/x-www-form-urlencoded",
    "multipart/form-data",
}
# Paths that bypass content-type validation (WebSockets, health checks, etc.)
CONTENT_TYPE_BYPASS_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware that validates incoming requests for:
    - Request size limits
    - Content-type validation
    - Request ID generation for tracing
    """

    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID for tracing
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        # Log incoming request
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )

        # Skip validation for bypass paths
        if request.url.path in CONTENT_TYPE_BYPASS_PATHS:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

        # Validate content-type for requests with body
        if request.method in ("POST", "PUT", "PATCH"):
            content_type = request.headers.get("content-type", "")
            # Extract base content-type (ignore charset and boundary params)
            base_content_type = content_type.split(";")[0].strip().lower()

            # Allow requests without body (empty content-type is OK)
            content_length = request.headers.get("content-length", "0")
            if content_length != "0" and base_content_type:
                if base_content_type not in ALLOWED_CONTENT_TYPES:
                    logger.warning(
                        f"[{request_id}] Invalid content-type: {base_content_type}"
                    )
                    return JSONResponse(
                        status_code=415,
                        content={
                            "detail": f"Unsupported content-type: {base_content_type}. "
                            f"Allowed: {', '.join(sorted(ALLOWED_CONTENT_TYPES))}"
                        },
                        headers={"X-Request-ID": request_id},
                    )

            # Validate request size via content-length header
            try:
                size = int(content_length)
                if size > MAX_REQUEST_SIZE:
                    logger.warning(
                        f"[{request_id}] Request too large: {size} bytes "
                        f"(max: {MAX_REQUEST_SIZE})"
                    )
                    return JSONResponse(
                        status_code=413,
                        content={
                            "detail": f"Request body too large. Maximum size is "
                            f"{MAX_REQUEST_SIZE // (1024 * 1024)}MB"
                        },
                        headers={"X-Request-ID": request_id},
                    )
            except ValueError:
                pass  # Invalid content-length header, let it through

        # Process request and add request ID to response
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        # Log response status
        logger.info(
            f"[{request_id}] Response: {response.status_code}"
        )

        return response

app = FastAPI(
    title="Ashwen",
    description="AI Agents Observability Platform for Project Builders",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:4173", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request validation middleware for size, content-type, and request ID tracing
app.add_middleware(RequestValidationMiddleware)

app.include_router(projects.router)
app.include_router(agents.router)
app.include_router(memory.router)
app.include_router(credentials.router)


@app.on_event("startup")
async def startup():
    await init_db()


@app.get("/health")
async def health():
    """
    Comprehensive health check endpoint.

    Returns detailed status of:
    - API status
    - Database connectivity
    - Encryption key configuration
    - Ollama availability
    """
    health_status = {
        "status": "ok",
        "version": "0.1.0",
        "checks": {
            "database": {"status": "unknown"},
            "encryption": {"status": "unknown"},
            "ollama": {"status": "unknown"},
        },
    }

    # Check database connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["checks"]["database"] = {
            "status": "ok",
            "type": "sqlite",
            "path": str(get_data_dir() / "ashwen.db"),
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["database"] = {
            "status": "error",
            "error": str(e),
        }

    # Check encryption key
    try:
        key = get_encryption_key()
        if key and len(key) >= 32:
            key_source = "env" if settings.encryption_key else "file"
            health_status["checks"]["encryption"] = {
                "status": "ok",
                "source": key_source,
            }
        else:
            health_status["status"] = "degraded"
            health_status["checks"]["encryption"] = {
                "status": "error",
                "error": "Encryption key is missing or invalid",
            }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["encryption"] = {
            "status": "error",
            "error": str(e),
        }

    # Check Ollama availability
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{settings.ollama_base_url}/api/tags",
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                health_status["checks"]["ollama"] = {
                    "status": "ok",
                    "base_url": settings.ollama_base_url,
                    "models_available": len(models),
                    "models": models[:5] if models else [],  # List first 5 models
                }
            else:
                health_status["status"] = "degraded"
                health_status["checks"]["ollama"] = {
                    "status": "error",
                    "base_url": settings.ollama_base_url,
                    "error": f"HTTP {response.status_code}",
                }
    except httpx.ConnectError:
        health_status["status"] = "degraded"
        health_status["checks"]["ollama"] = {
            "status": "unreachable",
            "base_url": settings.ollama_base_url,
            "error": "Connection refused",
        }
    except httpx.TimeoutException:
        health_status["status"] = "degraded"
        health_status["checks"]["ollama"] = {
            "status": "timeout",
            "base_url": settings.ollama_base_url,
            "error": "Connection timed out",
        }
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["ollama"] = {
            "status": "error",
            "base_url": settings.ollama_base_url,
            "error": str(e),
        }

    return health_status


async def _send_json_safe(websocket: WebSocket, payload: dict) -> bool:
    try:
        await websocket.send_json(payload)
        return True
    except RuntimeError:
        return False


async def _load_project_context(session, project_id: str, limit: int = 20) -> list[dict]:
    result = await session.execute(
        select(Message)
        .where(Message.project_id == project_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    history = list(result.scalars().all())
    history.reverse()
    return [{"role": msg.role, "content": msg.content} for msg in history]


async def _resolve_target_agents(
    session, project_id: str, selected_agent_id: str | None, is_dm: bool = False
) -> list[Agent]:
    """
    Resolve which agents should respond to a message.

    Args:
        session: Database session
        project_id: UUID of the project
        selected_agent_id: UUID of specifically selected agent (from UI)
        is_dm: Whether this is a direct message (only target selected agent)

    Returns:
        List of agents that should respond. For DM mode, returns only the selected agent.
        For group chat, returns the first available agent.
    """
    # DM mode: only target the specifically selected agent
    if is_dm and selected_agent_id:
        result = await session.execute(
            select(Agent).where(
                Agent.id == selected_agent_id,
                Agent.project_id == project_id,
            )
        )
        agent = result.scalar_one_or_none()
        return [agent] if agent else []

    # Non-DM mode with selected agent: still only target that agent
    if selected_agent_id:
        result = await session.execute(
            select(Agent).where(
                Agent.id == selected_agent_id,
                Agent.project_id == project_id,
            )
        )
        agent = result.scalar_one_or_none()
        return [agent] if agent else []

    # No agent selected: find first available agent by provider credentials
    providers_result = await session.execute(select(Credential.provider))
    configured_providers = {row[0] for row in providers_result.all()}

    result = await session.execute(
        select(Agent)
        .where(Agent.project_id == project_id)
        .order_by(Agent.created_at.asc())
    )
    all_agents = list(result.scalars().all())
    available_agents = [
        agent
        for agent in all_agents
        if agent.llm_provider == "ollama" or agent.llm_provider in configured_providers
    ]

    return available_agents[:1] or all_agents[:1]


@app.websocket("/ws/{project_id}")
async def project_websocket(websocket: WebSocket, project_id: str):
    await websocket.accept()
    logger.info(f"[WS] Client connected to project {project_id}")

    try:
        while True:
            payload = await websocket.receive_json()
            message_type = payload.get("type")

            # Handle ping/pong for connection health monitoring
            if message_type == "ping":
                await _send_json_safe(websocket, {
                    "type": "pong",
                    "timestamp": payload.get("timestamp"),
                })
                continue

            if message_type != "user:message":
                await _send_json_safe(
                    websocket,
                    {"type": "system:error", "detail": f"Unsupported message type: {message_type}"},
                )
                continue

            content = str(payload.get("content", "")).strip()
            selected_agent_id = payload.get("selected_agent_id")
            is_dm = payload.get("is_dm", False)

            if not content:
                await _send_json_safe(
                    websocket,
                    {"type": "system:error", "detail": "Message content is required"},
                )
                continue

            # Validate DM mode requirements
            if is_dm and not selected_agent_id:
                await _send_json_safe(
                    websocket,
                    {"type": "system:error", "detail": "DM mode requires a selected agent"},
                )
                continue

            async with async_session_maker() as session:
                project_result = await session.execute(select(Project).where(Project.id == project_id))
                project = project_result.scalar_one_or_none()
                if not project:
                    await _send_json_safe(
                        websocket,
                        {"type": "system:error", "detail": "Project not found"},
                    )
                    continue

                # Determine message type: DM mode uses "dm", otherwise "chat"
                msg_type = "dm" if is_dm and selected_agent_id else "chat"

                user_message = Message(
                    project_id=project_id,
                    agent_id=None,
                    role="user",
                    content=content,
                    message_type=msg_type,
                )
                session.add(user_message)
                await session.commit()
                await session.refresh(user_message)

                context_messages = await _load_project_context(session, project_id)
                target_agents = await _resolve_target_agents(
                    session, project_id, selected_agent_id, is_dm=is_dm
                )

                if not target_agents:
                    await _send_json_safe(
                        websocket,
                        {"type": "system:error", "detail": "No available agents for this project"},
                    )
                    continue

                for agent in target_agents:
                    await _send_json_safe(
                        websocket,
                        {"type": "agent:status", "agent_id": agent.id, "status": "thinking"},
                    )

                    try:
                        agent_service = AgentBase(agent, session)
                        stream = await agent_service.respond(context_messages, stream=True)

                        await _send_json_safe(
                            websocket,
                            {"type": "agent:status", "agent_id": agent.id, "status": "active"},
                        )

                        full_response = ""
                        async for chunk in stream:
                            full_response += chunk
                            if not await _send_json_safe(
                                websocket,
                                {"type": "agent:stream", "agent_id": agent.id, "chunk": chunk},
                            ):
                                break

                        full_response = full_response.strip()
                        if full_response:
                            assistant_message = Message(
                                project_id=project_id,
                                agent_id=agent.id,
                                role="assistant",
                                content=full_response,
                                message_type=msg_type,
                            )
                            session.add(assistant_message)
                            await session.commit()
                            await session.refresh(assistant_message)

                            await _send_json_safe(
                                websocket,
                                {
                                    "type": "agent:message",
                                    "agent_id": agent.id,
                                    "content": full_response,
                                    "confidence": None,
                                    "message_type": msg_type,
                                },
                            )
                    except Exception as exc:
                        await _send_json_safe(
                            websocket,
                            {
                                "type": "system:error",
                                "detail": f"{agent.name} failed: {str(exc)}",
                            },
                        )
                    finally:
                        await _send_json_safe(
                            websocket,
                            {"type": "agent:status", "agent_id": agent.id, "status": "idle"},
                        )
    except WebSocketDisconnect:
        return
