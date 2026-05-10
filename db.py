import asyncpg
import logging
from config import settings

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = settings.DATABASE_URL
        if not dsn:
            raise RuntimeError("DATABASE_URL not configured")
        _pool = await asyncpg.create_pool(dsn, min_size=1, max_size=5)
        logger.info("PostgreSQL pool created")
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        logger.info("PostgreSQL pool closed")


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS audits (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                idea TEXT NOT NULL,
                model_used TEXT,
                cost_usd REAL DEFAULT 0,
                tokens_used INTEGER DEFAULT 0,
                input_hash TEXT,
                output_hash TEXT,
                prev_hash TEXT,
                chain_hash TEXT,
                disclaimer_accepted INTEGER DEFAULT 1,
                jurisdiction TEXT DEFAULT 'EU',
                timestamp TEXT NOT NULL
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                company_name TEXT DEFAULT '',
                status TEXT DEFAULT 'active',
                documents JSONB DEFAULT '[]',
                result JSONB DEFAULT NULL,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_audits_user ON audits(user_id)
        """)
    logger.info("Database tables initialized")
