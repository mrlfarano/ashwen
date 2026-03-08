# Database Connection Pooling Configuration

This document explains the database connection pooling configuration implemented in Ashwen.

## Overview

The SQLAlchemy engine is now configured with connection pooling settings to handle concurrent requests efficiently. The configuration is optimized based on the database backend being used.

## Configuration Settings

The following environment variables can be set to configure connection pooling (in `.env` file):

| Setting | Default | Description |
|---------|---------|-------------|
| `db_pool_size` | 5 | Number of connections to keep in the pool (not used with SQLite) |
| `db_max_overflow` | 10 | Maximum number of connections beyond pool_size (not used with SQLite) |
| `db_pool_timeout` | 30 | Seconds to wait for a connection from the pool |
| `db_pool_recycle` | 3600 | Recycle connections after N seconds (1 hour) |
| `db_pool_pre_ping` | True | Test connection health before use |

### SQLite Configuration

SQLite has specific limitations with concurrent writes, so it uses a `NullPool` by default:
- **No connection pooling**: Each database checkout creates a new connection
- **Why**: SQLite uses file-based locking that can cause conflicts with pooled connections
- **Safe for async**: Works well with `aiosqlite` for concurrent reads

### PostgreSQL/MySQL Configuration

When using PostgreSQL or MySQL, the connection pool uses these settings:
- **pool_size**: 5 connections maintained in the pool
- **max_overflow**: Up to 10 additional connections can be created during peak load
- **pool_timeout**: Wait up to 30 seconds for an available connection
- **pool_recycle**: Connections are recycled after 1 hour to prevent stale connections
- **pool_pre_ping**: Connections are tested before use to ensure they're alive

## Implementation Details

### Files Modified

1. **backend/app/config.py**: Added connection pooling settings to the `Settings` class
2. **backend/app/database.py**: Configured the async engine with pooling parameters

### Code Structure

```python
# In database.py
engine_args = {
    "echo": settings.debug,
    "pool_pre_ping": settings.db_pool_pre_ping,
    "pool_recycle": settings.db_pool_recycle,
}

# SQLite: Use NullPool (no pooling)
if "sqlite" in get_database_url():
    engine_args["poolclass"] = NullPool
# PostgreSQL/MySQL: Use connection pooling
else:
    engine_args["pool_size"] = settings.db_pool_size
    engine_args["max_overflow"] = settings.db_max_overflow
    engine_args["pool_timeout"] = settings.db_pool_timeout

engine = create_async_engine(get_database_url(), **engine_args)
```

## Benefits

1. **Efficient Resource Usage**: Reuses database connections instead of creating new ones
2. **Better Concurrency**: Handles multiple simultaneous requests without exhausting connections
3. **Connection Health**: Pre-ping ensures stale connections are detected and replaced
4. **Production Ready**: When migrating to PostgreSQL/MySQL, pooling is already configured

## Monitoring

You can check the database connection status via the health endpoint:
```bash
curl http://localhost:8000/health
```

This will show the database type and path (for SQLite) in the response.

## Production Considerations

When deploying to production with PostgreSQL or MySQL:

1. Set appropriate pool sizes based on your expected concurrent load
2. Monitor connection usage to tune `pool_size` and `max_overflow`
3. Adjust `pool_recycle` based on your database's connection timeout settings
4. Ensure `pool_pre_ping` remains enabled to handle connection drops

Example `.env` for production:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost/ashwen
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
DB_POOL_PRE_PING=true
```
