from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.config import logger, settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session = None
    try:
        session = async_session()
        yield session

        # Explicitly commit if there are pending changes
        if session.dirty or session.new or session.deleted:
            await session.commit()

    except Exception as e:
        if session:
            try:
                await session.rollback()
                logger.warning(
                    f"Rolled back session {id(session)} due to error: {str(e)}"
                )
            except Exception as rollback_error:
                logger.critical(f"Error during rollback: {rollback_error}")
        raise
    finally:
        if session:
            try:
                await session.close()
            except Exception as close_error:
                logger.critical(f"Error closing session: {close_error}")


async def check_connection() -> bool:
    try:
        async with get_db_session() as session:
            result = await session.execute(text("SELECT 1"))
            result.fetchone()
        return True
    except Exception as e:
        logger.fatal(f"Database connection error: {e}")
        return False


async def cleanup_connections():
    try:
        await engine.dispose()
        logger.info("Database engine disposed successfully")
    except Exception as e:
        logger.error(f"Error disposing engine: {e}")
