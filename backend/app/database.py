from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.config import get_database_url, settings

# Build engine arguments with connection pooling configuration
# Note: SQLite with aiosqlite works best with NullPool (no pooling) or QueuePool with pool_size=1
# because SQLite has limitations with concurrent writes
engine_args = {
    "echo": settings.debug,
    "pool_pre_ping": settings.db_pool_pre_ping,
    "pool_recycle": settings.db_pool_recycle,
}

# SQLite-specific pooling configuration
# NullPool creates a new connection for each checkout, which is safer for SQLite
# For production with PostgreSQL/MySQL, you would want QueuePool with larger pool_size
if "sqlite" in get_database_url():
    # SQLite works best with NullPool to avoid database locking issues
    engine_args["poolclass"] = NullPool
else:
    # For production databases (PostgreSQL, MySQL), use connection pooling
    engine_args["pool_size"] = settings.db_pool_size
    engine_args["max_overflow"] = settings.db_max_overflow
    engine_args["pool_timeout"] = settings.db_pool_timeout

engine = create_async_engine(get_database_url(), **engine_args)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session
