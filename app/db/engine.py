from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.settings import settings


@lru_cache(maxsize=1)
def get_async_engine():
    """Create and cache a singleton async SQLAlchemy engine."""
    connect_args = {"ssl": "require"} if settings.db_ssl_require else {}
    return create_async_engine(
        settings.async_database_url,
        echo=settings.db_echo,
        future=True,
        connect_args=connect_args,
    )


@lru_cache(maxsize=1)
def get_async_session_factory():
    """Create and cache a singleton async session factory."""
    return async_sessionmaker(
        bind=get_async_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


def get_sync_engine():
    """Lazily create a sync engine for Alembic migrations."""
    from sqlalchemy import create_engine

    return create_engine(settings.sync_database_url, echo=settings.db_echo)
