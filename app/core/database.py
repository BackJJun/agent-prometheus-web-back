from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True, poolclass=NullPool)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_db_session() -> AsyncIterator[AsyncSession]:
    session_factory = get_sessionmaker()
    async with session_factory() as session:
        yield session


async def fetch_database_health() -> dict[str, object]:
    async with get_engine().connect() as connection:
        database = await connection.scalar(text("select current_database()"))
        rows = await connection.execute(
            text(
                """
                select extname
                from pg_extension
                where extname in ('pgcrypto', 'vector')
                """
            )
        )
        installed = {row[0] for row in rows}

    return {
        "status": "ok",
        "database": database,
        "extensions": {
            "pgcrypto": "pgcrypto" in installed,
            "vector": "vector" in installed,
        },
    }
