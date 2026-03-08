"""
Local Memory Storage with SQLite FTS5 for full-text search.

This module replaces LanceDB with a pure Python sqlite3-based solution using FTS5
for full-text search. It's lighter weight, has no external dependencies beyond
the Python standard library, and is well-suited for local-first desktop apps.

For embeddings-based semantic search, you can optionally use sqlite-vec extension,
but FTS5 provides excellent search quality for most use cases.
"""

import asyncio
import json
import logging
import re
import sqlite3
import threading
from collections.abc import AsyncIterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, Union
import hashlib

logger = logging.getLogger(__name__)

# Valid memory types
VALID_MEMORY_TYPES = frozenset({"decision", "pattern", "context", "learning", "note", "episodic", "semantic", "procedural"})


class MemoryDocument:
    """Simple dataclass for memory documents."""
    
    def __init__(
        self,
        id: str,
        project_id: str,
        memory_type: str,
        title: str,
        content: str,
        metadata: dict,
        created_at: datetime,
        updated_at: datetime,
        file_path: Optional[str] = None,
    ):
        self.id = id
        self.project_id = project_id
        self.memory_type = memory_type
        self.title = title
        self.content = content
        self.metadata = metadata
        self.created_at = created_at
        self.updated_at = updated_at
        self.file_path = file_path

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "memory_type": self.memory_type,
            "title": self.title,
            "content": self.content,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "file_path": self.file_path,
        }


class SQLiteFTSStore:
    """
    SQLite-based storage with FTS5 full-text search.
    
    Thread-safe implementation using connection-per-thread pattern.
    Uses WAL mode for better concurrent read/write performance.
    """
    
    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=30.0,
                check_same_thread=False,
            )
            # Enable WAL mode for better concurrency
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")  # 64MB cache
            conn.row_factory = sqlite3.Row
            self._local.connection = conn
        return self._local.connection
    
    def _init_db(self):
        """Initialize database schema with FTS5 tables."""
        conn = self._get_connection()
        
        # Main memory entries table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                file_path TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Index for faster project/type queries
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_project_type 
            ON memory_entries(project_id, memory_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_memory_updated 
            ON memory_entries(project_id, updated_at DESC)
        """)
        
        # FTS5 virtual table for full-text search
        # Using unicode61 tokenizer with remove_diacritics for better search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(
                id UNINDEXED,
                project_id UNINDEXED,
                memory_type,
                title,
                content,
                content='memory_entries',
                content_rowid='rowid',
                tokenize='unicode61 remove_diacritics 2'
            )
        """)
        
        # Triggers to keep FTS in sync with main table
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memory_ai AFTER INSERT ON memory_entries BEGIN
                INSERT INTO memory_fts(rowid, id, project_id, memory_type, title, content)
                VALUES (new.rowid, new.id, new.project_id, new.memory_type, new.title, new.content);
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memory_ad AFTER DELETE ON memory_entries BEGIN
                INSERT INTO memory_fts(memory_fts, rowid, id, project_id, memory_type, title, content)
                VALUES ('delete', old.rowid, old.id, old.project_id, old.memory_type, old.title, old.content);
            END
        """)
        
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memory_au AFTER UPDATE ON memory_entries BEGIN
                INSERT INTO memory_fts(memory_fts, rowid, id, project_id, memory_type, title, content)
                VALUES ('delete', old.rowid, old.id, old.project_id, old.memory_type, old.title, old.content);
                INSERT INTO memory_fts(rowid, id, project_id, memory_type, title, content)
                VALUES (new.rowid, new.id, new.project_id, new.memory_type, new.title, new.content);
            END
        """)
        
        conn.commit()
        logger.info(f"Initialized SQLite FTS5 store at {self.db_path}")
    
    def add(self, doc: MemoryDocument) -> bool:
        """Add or update a memory document."""
        conn = self._get_connection()
        try:
            conn.execute("""
                INSERT OR REPLACE INTO memory_entries 
                (id, project_id, memory_type, title, content, metadata, file_path, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc.id,
                doc.project_id,
                doc.memory_type,
                doc.title,
                doc.content,
                json.dumps(doc.metadata),
                doc.file_path,
                doc.created_at.isoformat() if isinstance(doc.created_at, datetime) else doc.created_at,
                doc.updated_at.isoformat() if isinstance(doc.updated_at, datetime) else doc.updated_at,
            ))
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Failed to add memory document {doc.id}: {e}")
            conn.rollback()
            return False
    
    def search(
        self,
        query: str,
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> list[dict]:
        """
        Full-text search using FTS5.
        
        Supports:
        - Prefix search: "react*" matches "react", "reactive", "reactor"
        - Phrase search: "\"exact phrase\""
        - Boolean operators: "react AND vue", "python OR ruby", "NOT java"
        - NEAR operator: "api NEAR/5 rest"
        - Column-specific: "title:config content:settings"
        """
        conn = self._get_connection()
        
        # Sanitize and prepare query for FTS5
        fts_query = self._prepare_fts_query(query)
        
        # Build the search query
        sql = """
            SELECT m.id, m.project_id, m.memory_type, m.title, m.content, 
                   m.metadata, m.file_path, m.created_at, m.updated_at,
                   bm25(memory_fts) as relevance
            FROM memory_fts fts
            JOIN memory_entries m ON fts.id = m.id
            WHERE memory_fts MATCH ?
        """
        params = [fts_query]
        
        if project_id:
            sql += " AND m.project_id = ?"
            params.append(project_id)
        
        if memory_type:
            sql += " AND m.memory_type = ?"
            params.append(memory_type)
        
        sql += " ORDER BY relevance LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        try:
            cursor = conn.execute(sql, params)
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "project_id": row["project_id"],
                    "memory_type": row["memory_type"],
                    "title": row["title"],
                    "content": row["content"],
                    "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                    "file_path": row["file_path"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "relevance": row["relevance"],
                })
            return results
        except sqlite3.Error as e:
            logger.error(f"FTS search failed for query '{query}': {e}")
            # Fallback to LIKE search
            return self._fallback_search(query, project_id, memory_type, limit)
    
    def _prepare_fts_query(self, query: str) -> str:
        """
        Prepare a user query for FTS5.
        
        FTS5 has special characters: { } [ ] ( ) : * ^ " 
        We need to escape or handle these appropriately.
        """
        # If query already looks like an advanced FTS query, use it as-is
        if any(op in query.upper() for op in [' AND ', ' OR ', ' NOT ', ' NEAR ']):
            return query
        if query.startswith('"') and query.endswith('"'):
            return query
        if ':' in query:  # Column-specific query
            return query
        
        # Simple query: escape special chars and add prefix wildcards to words
        # Remove FTS5 special characters
        cleaned = re.sub(r'[{}()\[\]^]', ' ', query)
        
        # Split into words and add prefix matching
        words = cleaned.split()
        if not words:
            return query  # Return original if we have nothing
        
        # Add * for prefix matching on each word
        fts_words = []
        for word in words:
            if len(word) >= 2:
                fts_words.append(f"{word}*")
            else:
                fts_words.append(word)
        
        return " ".join(fts_words)
    
    def _fallback_search(
        self,
        query: str,
        project_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """Fallback to LIKE search if FTS fails."""
        conn = self._get_connection()
        
        sql = """
            SELECT id, project_id, memory_type, title, content, 
                   metadata, file_path, created_at, updated_at
            FROM memory_entries
            WHERE (title LIKE ? OR content LIKE ?)
        """
        like_term = f"%{query}%"
        params = [like_term, like_term]
        
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        
        cursor = conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "project_id": row["project_id"],
                "memory_type": row["memory_type"],
                "title": row["title"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "file_path": row["file_path"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return results
    
    def list_entries(
        self,
        project_id: str,
        memory_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List memory entries for a project."""
        conn = self._get_connection()
        
        sql = """
            SELECT id, project_id, memory_type, title, content, 
                   metadata, file_path, created_at, updated_at
            FROM memory_entries
            WHERE project_id = ?
        """
        params = [project_id]
        
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        
        sql += " ORDER BY updated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = conn.execute(sql, params)
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row["id"],
                "project_id": row["project_id"],
                "memory_type": row["memory_type"],
                "title": row["title"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "file_path": row["file_path"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            })
        return results
    
    def get(self, doc_id: str) -> Optional[dict]:
        """Get a single memory entry by ID."""
        conn = self._get_connection()
        
        cursor = conn.execute("""
            SELECT id, project_id, memory_type, title, content, 
                   metadata, file_path, created_at, updated_at
            FROM memory_entries
            WHERE id = ?
        """, (doc_id,))
        
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "project_id": row["project_id"],
                "memory_type": row["memory_type"],
                "title": row["title"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "file_path": row["file_path"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        return None
    
    def delete(self, doc_id: str) -> bool:
        """Delete a memory entry by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute("DELETE FROM memory_entries WHERE id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.Error as e:
            logger.error(f"Failed to delete memory entry {doc_id}: {e}")
            conn.rollback()
            return False
    
    def delete_by_project(self, project_id: str) -> int:
        """Delete all memory entries for a project."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM memory_entries WHERE project_id = ?",
                (project_id,)
            )
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Failed to delete memory entries for project {project_id}: {e}")
            conn.rollback()
            return 0
    
    def count(self, project_id: Optional[str] = None, memory_type: Optional[str] = None) -> int:
        """Count memory entries."""
        conn = self._get_connection()
        
        sql = "SELECT COUNT(*) FROM memory_entries"
        params = []
        conditions = []
        
        if project_id:
            conditions.append("project_id = ?")
            params.append(project_id)
        if memory_type:
            conditions.append("memory_type = ?")
            params.append(memory_type)
        
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        
        cursor = conn.execute(sql, params)
        return cursor.fetchone()[0]
    
    def close(self):
        """Close the database connection for this thread."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None


class FileStore:
    """
    File-based storage for memory content (markdown files).
    
    Provides human-readable storage alongside the SQLite database.
    """
    
    def __init__(self, project_path: Union[str, Path]):
        self.project_path = Path(project_path)
        self.memory_path = self.project_path / ".ashwen" / "memory"
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Create memory directory structure."""
        for mem_type in ["episodic", "semantic", "procedural"]:
            (self.memory_path / mem_type).mkdir(parents=True, exist_ok=True)
    
    def save(self, memory_type: str, filename: str, content: str) -> Path:
        """Save content to a markdown file."""
        # Validate memory type to prevent path traversal
        if memory_type not in VALID_MEMORY_TYPES:
            memory_type = "note"
        
        file_path = self.memory_path / memory_type / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return file_path
    
    def read(self, memory_type: str, filename: str) -> Optional[str]:
        """Read content from a markdown file."""
        if memory_type not in VALID_MEMORY_TYPES:
            return None
        
        file_path = self.memory_path / memory_type / filename
        if file_path.exists():
            return file_path.read_text(encoding="utf-8")
        return None
    
    def list_files(self, memory_type: Optional[str] = None) -> list[Path]:
        """List memory files."""
        if memory_type:
            if memory_type not in VALID_MEMORY_TYPES:
                return []
            path = self.memory_path / memory_type
            if path.exists():
                return list(path.glob("*.md"))
        else:
            files = []
            for mem_type in VALID_MEMORY_TYPES:
                path = self.memory_path / mem_type
                if path.exists():
                    files.extend(path.glob("*.md"))
            return files
        return []
    
    def delete(self, memory_type: str, filename: str) -> bool:
        """Delete a memory file."""
        if memory_type not in VALID_MEMORY_TYPES:
            return False
        
        file_path = self.memory_path / memory_type / filename
        if file_path.exists():
            file_path.unlink()
            return True
        return False


class LocalMemoryService:
    """
    Local memory service combining SQLite FTS5 storage with file-based backup.
    
    This is the main service class for memory management, replacing the
    previous HybridMemoryService that used LanceDB.
    """
    
    def __init__(self, project_id: str, project_path: Union[str, Path]):
        self.project_id = project_id
        self.project_path = Path(project_path)
        
        # SQLite database in project's .ashwen directory
        self.db_path = self.project_path / ".ashwen" / "memory.db"
        self.fts_store = SQLiteFTSStore(self.db_path)
        self.file_store = FileStore(self.project_path)
    
    async def index_content(
        self,
        memory_id: str,
        memory_type: str,
        title: str,
        content: str,
        metadata: Optional[dict] = None,
        save_file: bool = True,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ) -> MemoryDocument:
        """
        Index content in the local memory store.
        
        Args:
            memory_id: Unique identifier for this memory
            memory_type: Type of memory (decision, pattern, context, etc.)
            title: Memory title
            content: Memory content
            metadata: Optional metadata dict
            save_file: Whether to also save as a markdown file
            created_at: Creation timestamp (defaults to now)
            updated_at: Update timestamp (defaults to now)
            
        Returns:
            MemoryDocument: The indexed document
        """
        now = datetime.utcnow()
        created_at = created_at or now
        updated_at = updated_at or now
        
        file_path = None
        if save_file:
            filename = f"{memory_id}.md"
            file_content = f"# {title}\n\n{content}"
            file_path_obj = await asyncio.to_thread(
                self.file_store.save, memory_type, filename, file_content
            )
            file_path = str(file_path_obj.relative_to(self.project_path))
        
        doc = MemoryDocument(
            id=memory_id,
            project_id=self.project_id,
            memory_type=memory_type,
            title=title,
            content=content,
            metadata=metadata or {},
            created_at=created_at,
            updated_at=updated_at,
            file_path=file_path,
        )
        
        # Store in SQLite FTS
        await asyncio.to_thread(self.fts_store.add, doc)
        
        logger.debug(f"Indexed memory {memory_id} in local store")
        return doc
    
    async def search(
        self,
        query: str,
        memory_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Search memory using FTS5 full-text search.
        
        Args:
            query: Search query (supports FTS5 syntax)
            memory_type: Optional filter by memory type
            limit: Maximum results to return
            
        Returns:
            List of matching memory entries
        """
        results = await asyncio.to_thread(
            self.fts_store.search,
            query,
            self.project_id,
            memory_type,
            limit,
        )
        
        logger.debug(f"FTS search for '{query}' returned {len(results)} results")
        return results
    
    async def list_entries(
        self,
        memory_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """List memory entries for this project."""
        return await asyncio.to_thread(
            self.fts_store.list_entries,
            self.project_id,
            memory_type,
            limit,
            offset,
        )
    
    async def get(self, memory_id: str) -> Optional[dict]:
        """Get a specific memory entry."""
        result = await asyncio.to_thread(self.fts_store.get, memory_id)
        if result and result.get("project_id") == self.project_id:
            return result
        return None
    
    async def delete(self, memory_id: str, memory_type: str) -> bool:
        """Delete a memory entry from both SQLite and file storage."""
        # Delete from SQLite
        deleted = await asyncio.to_thread(self.fts_store.delete, memory_id)
        
        # Delete file
        filename = f"{memory_id}.md"
        await asyncio.to_thread(self.file_store.delete, memory_type, filename)
        
        return deleted
    
    async def delete_all(self) -> int:
        """Delete all memory entries for this project."""
        count = await asyncio.to_thread(
            self.fts_store.delete_by_project, self.project_id
        )
        return count
    
    async def count(self, memory_type: Optional[str] = None) -> int:
        """Count memory entries for this project."""
        return await asyncio.to_thread(
            self.fts_store.count, self.project_id, memory_type
        )
    
    def close(self):
        """Close database connections."""
        self.fts_store.close()


# Async context manager for memory service
@contextmanager
def get_memory_service(project_id: str, project_path: str):
    """Context manager for LocalMemoryService."""
    service = LocalMemoryService(project_id, project_path)
    try:
        yield service
    finally:
        service.close()
