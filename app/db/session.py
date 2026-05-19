from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.engine import get_async_session_factory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped async DB session. Commits on success, rolls back on error."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
