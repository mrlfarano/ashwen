"""
Memory Router - Handles memory entry CRUD and search operations.
Uses SQLite FTS5 for full-text search capabilities.
"""
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import MemoryEntry, Project
from app.schemas import (
    DeleteResponse,
    MemoryCreate,
    MemoryEntryResponse,
    MemoryUpdate,
    serialize_memory_entry,
)

router = APIRouter(prefix="/memory", tags=["memory"])
logger = logging.getLogger(__name__)

# Valid memory types
VALID_MEMORY_TYPES = {"episodic", "semantic", "procedural"}


def get_fts_db_path(project_path: str) -> Path:
    """Get the path to the FTS5 database for a project."""
    return Path(project_path) / ".ashwen" / "memory.db"


def init_fts_tables(conn: sqlite3.Connection):
    """Initialize FTS5 virtual table for memory search."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memory_fts (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL,
            memory_type TEXT NOT NULL,
            title TEXT,
            content TEXT,
            metadata TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    
    # Create FTS5 virtual table for full-text search
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts_idx USING fts5(
            id,
            title,
            content,
            memory_type,
            content='memory_fts',
            content_rowid='rowid',
            tokenize='porter unicode61'
        )
    """)
    
    # Triggers to keep FTS index in sync
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memory_fts_ai AFTER INSERT ON memory_fts BEGIN
            INSERT INTO memory_fts_idx(rowid, id, title, content, memory_type)
            VALUES (new.rowid, new.id, new.title, new.content, new.memory_type);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memory_fts_ad AFTER DELETE ON memory_fts BEGIN
            INSERT INTO memory_fts_idx(memory_fts_idx, rowid, id, title, content, memory_type)
            VALUES('delete', old.rowid, old.id, old.title, old.content, old.memory_type);
        END
    """)
    
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memory_fts_au AFTER UPDATE ON memory_fts BEGIN
            INSERT INTO memory_fts_idx(memory_fts_idx, rowid, id, title, content, memory_type)
            VALUES('delete', old.rowid, old.id, old.title, old.content, old.memory_type);
            INSERT INTO memory_fts_idx(rowid, id, title, content, memory_type)
            VALUES (new.rowid, new.id, new.title, new.content, new.memory_type);
        END
    """)
    
    conn.commit()


@asynccontextmanager
async def get_fts_connection(project_path: str):
    """Get an FTS database connection with proper initialization."""
    db_path = get_fts_db_path(project_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        init_fts_tables(conn)
        yield conn
    finally:
        conn.close()


async def index_memory_in_fts(
    conn: sqlite3.Connection,
    memory_id: str,
    project_id: str,
    memory_type: str,
    title: str,
    content: str,
    metadata: dict,
):
    """Index a memory entry in FTS5."""
    now = datetime.utcnow().isoformat()
    conn.execute("""
        INSERT OR REPLACE INTO memory_fts 
        (id, project_id, memory_type, title, content, metadata, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        memory_id,
        project_id,
        memory_type,
        title,
        content,
        json.dumps(metadata),
        now,
        now,
    ))
    conn.commit()


async def search_fts(
    conn: sqlite3.Connection,
    query: str,
    memory_type: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
) -> list[dict]:
    """
    Search memory using FTS5 full-text search.
    
    Uses BM25 ranking for relevance scoring.
    """
    # Sanitize query for FTS5
    query = query.replace("'", "''")
    
    if memory_type:
        sql = """
            SELECT m.*, bm25(memory_fts_idx) as rank
            FROM memory_fts_idx fts
            JOIN memory_fts m ON fts.id = m.id
            WHERE memory_fts_idx MATCH ? AND m.memory_type = ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        """
        cursor = conn.execute(sql, (query, memory_type, limit, offset))
    else:
        sql = """
            SELECT m.*, bm25(memory_fts_idx) as rank
            FROM memory_fts_idx fts
            JOIN memory_fts m ON fts.id = m.id
            WHERE memory_fts_idx MATCH ?
            ORDER BY rank
            LIMIT ? OFFSET ?
        """
        cursor = conn.execute(sql, (query, limit, offset))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            "id": row["id"],
            "project_id": row["project_id"],
            "memory_type": row["memory_type"],
            "title": row["title"],
            "content": row["content"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "rank": row["rank"],
        })
    
    return results


async def delete_from_fts(conn: sqlite3.Connection, memory_id: str):
    """Delete a memory entry from the FTS index."""
    conn.execute("DELETE FROM memory_fts WHERE id = ?", (memory_id,))
    conn.commit()


@router.get("/project/{project_id}", response_model=list[MemoryEntryResponse])
async def list_project_memory(
    project_id: str,
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    limit: int = Query(50, ge=1, le=200, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    session: AsyncSession = Depends(get_session),
):
    """
    List all memory entries for a project with optional filtering.
    
    Args:
        project_id: UUID of the project
        memory_type: Optional filter by memory type (episodic, semantic, procedural)
        limit: Maximum number of results
        offset: Pagination offset
        
    Returns:
        List[MemoryEntry]: Memory entries for the project
    """
    if memory_type and memory_type not in VALID_MEMORY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid memory type. Must be one of: {', '.join(VALID_MEMORY_TYPES)}"
        )
    
    try:
        # Verify project exists and get path
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Query memory entries
        query = select(MemoryEntry).where(MemoryEntry.project_id == project_id)
        
        if memory_type:
            query = query.where(MemoryEntry.memory_type == memory_type)
        
        query = query.order_by(MemoryEntry.updated_at.desc()).limit(limit).offset(offset)
        
        result = await session.execute(query)
        entries = result.scalars().all()
        
        return [serialize_memory_entry(entry) for entry in entries]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing memory for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory entries"
        )


@router.post("/project/{project_id}", status_code=status.HTTP_201_CREATED, response_model=MemoryEntryResponse)
async def create_memory(
    project_id: str,
    payload: MemoryCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new memory entry with FTS5 indexing.
    
    Args:
        project_id: UUID of the project
        payload: Memory creation data
        
    Returns:
        MemoryEntry: The newly created memory entry
    """
    if payload.memory_type not in VALID_MEMORY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid memory type. Must be one of: {', '.join(VALID_MEMORY_TYPES)}"
        )
    
    if not payload.title or not payload.title.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Memory title is required"
        )
    
    if not payload.content or not payload.content.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Memory content is required"
        )
    
    try:
        # Verify project exists and get path
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Create memory entry in main database
        entry = MemoryEntry(
            project_id=project_id,
            memory_type=payload.memory_type,
            title=payload.title.strip(),
            content=payload.content.strip(),
            entry_metadata=json.dumps(payload.metadata),
        )
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        
        # Index in FTS5
        try:
            async with get_fts_connection(project.path) as fts_conn:
                await index_memory_in_fts(
                    fts_conn,
                    entry.id,
                    project_id,
                    payload.memory_type,
                    payload.title.strip(),
                    payload.content.strip(),
                    payload.metadata,
                )
        except Exception as e:
            logger.warning(f"Failed to index memory in FTS: {e}")
            # Don't fail the request - entry is still in main DB
        
        logger.info(f"Created memory entry {entry.id} for project {project_id}")
        return serialize_memory_entry(entry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating memory entry: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create memory entry"
        )


@router.get("/{memory_id}", response_model=MemoryEntryResponse)
async def get_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific memory entry by ID.
    """
    if not memory_id or not memory_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Memory ID is required"
        )
    
    try:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory entry with ID '{memory_id}' not found"
            )
        
        return serialize_memory_entry(entry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving memory {memory_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve memory entry"
        )


@router.patch("/{memory_id}", response_model=MemoryEntryResponse)
async def update_memory(
    memory_id: str,
    payload: MemoryUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Update a memory entry and re-index in FTS5.
    """
    if not memory_id or not memory_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Memory ID is required"
        )
    
    try:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory entry with ID '{memory_id}' not found"
            )
        
        # Get project for FTS update
        project_result = await session.execute(select(Project).where(Project.id == entry.project_id))
        project = project_result.scalar_one_or_none()
        
        # Track if we need to re-index
        needs_reindex = False
        
        if payload.title is not None:
            if not payload.title.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Memory title cannot be empty"
                )
            entry.title = payload.title.strip()
            needs_reindex = True
        
        if payload.content is not None:
            if not payload.content.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Memory content cannot be empty"
                )
            entry.content = payload.content.strip()
            needs_reindex = True
        
        if payload.metadata is not None:
            entry.entry_metadata = json.dumps(payload.metadata)
            needs_reindex = True
        
        await session.commit()
        await session.refresh(entry)
        
        # Re-index in FTS5 if needed
        if needs_reindex and project:
            try:
                async with get_fts_connection(project.path) as fts_conn:
                    await index_memory_in_fts(
                        fts_conn,
                        entry.id,
                        entry.project_id,
                        entry.memory_type,
                        entry.title,
                        entry.content,
                        json.loads(entry.entry_metadata) if entry.entry_metadata else {},
                    )
            except Exception as e:
                logger.warning(f"Failed to re-index memory in FTS: {e}")
        
        logger.info(f"Updated memory entry {memory_id}")
        return serialize_memory_entry(entry)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating memory {memory_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update memory entry"
        )


@router.delete("/{memory_id}", response_model=DeleteResponse)
async def delete_memory(
    memory_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a memory entry from both main database and FTS index.
    """
    if not memory_id or not memory_id.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Memory ID is required"
        )
    
    try:
        result = await session.execute(select(MemoryEntry).where(MemoryEntry.id == memory_id))
        entry = result.scalar_one_or_none()
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Memory entry with ID '{memory_id}' not found"
            )
        
        # Get project for FTS deletion
        project_result = await session.execute(select(Project).where(Project.id == entry.project_id))
        project = project_result.scalar_one_or_none()
        
        await session.delete(entry)
        await session.commit()
        
        # Remove from FTS index
        if project:
            try:
                async with get_fts_connection(project.path) as fts_conn:
                    await delete_from_fts(fts_conn, memory_id)
            except Exception as e:
                logger.warning(f"Failed to delete memory from FTS: {e}")
        
        logger.info(f"Deleted memory entry {memory_id}")
        return {"deleted": True, "memory_id": memory_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting memory {memory_id}: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete memory entry"
        )


@router.get("/project/{project_id}/search", response_model=list[dict])
async def search_memory(
    project_id: str,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    memory_type: Optional[str] = Query(None, description="Filter by memory type"),
    limit: int = Query(10, ge=1, le=100, description="Max results"),
    session: AsyncSession = Depends(get_session),
):
    """
    Full-text search across memory entries using FTS5.
    
    Supports advanced search syntax:
    - Word search: `q=database`
    - Phrase search: `q="local memory"`
    - Prefix search: `q=sql*`
    - Boolean AND: `q=sqlite AND memory` (default behavior)
    - Boolean OR: `q=sqlite OR lancedb`
    - Negation: `q=sqlite NOT remote`
    """
    if memory_type and memory_type not in VALID_MEMORY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid memory type. Must be one of: {', '.join(VALID_MEMORY_TYPES)}"
        )
    
    try:
        # Verify project exists and get path
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Search in FTS5
        async with get_fts_connection(project.path) as fts_conn:
            results = await search_fts(fts_conn, q, memory_type, limit)
        
        logger.info(f"FTS search for '{q}' returned {len(results)} results")
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to search memory entries"
        )


@router.post("/project/{project_id}/reindex", response_model=dict)
async def reindex_project_memory(
    project_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Rebuild the FTS5 index for a project.
    Useful after database migrations or index corruption.
    """
    try:
        # Verify project exists and get path
        result = await session.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with ID '{project_id}' not found"
            )
        
        # Get all memory entries
        entries_result = await session.execute(
            select(MemoryEntry).where(MemoryEntry.project_id == project_id)
        )
        entries = entries_result.scalars().all()
        
        # Rebuild FTS index
        async with get_fts_connection(project.path) as fts_conn:
            # Clear existing index
            fts_conn.execute("DELETE FROM memory_fts WHERE project_id = ?", (project_id,))
            fts_conn.commit()
            
            # Re-index all entries
            indexed_count = 0
            for entry in entries:
                try:
                    await index_memory_in_fts(
                        fts_conn,
                        entry.id,
                        entry.project_id,
                        entry.memory_type,
                        entry.title,
                        entry.content,
                        json.loads(entry.entry_metadata) if entry.entry_metadata else {},
                    )
                    indexed_count += 1
                except Exception as e:
                    logger.warning(f"Failed to index entry {entry.id}: {e}")
        
        logger.info(f"Re-indexed {indexed_count} memory entries for project {project_id}")
        return {
            "reindexed": True,
            "project_id": project_id,
            "entries_indexed": indexed_count,
            "total_entries": len(entries),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error re-indexing project memory: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to re-index memory"
        )
