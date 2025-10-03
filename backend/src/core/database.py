"""
Database configuration and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import redis.asyncio as redis
from typing import AsyncGenerator

from .config import settings

# SQLAlchemy setup
engine = create_engine(
    settings.database_url_computed,
    poolclass=StaticPool,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Redis setup
redis_client: redis.Redis = None


def get_db() -> AsyncGenerator:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_redis() -> redis.Redis:
    """Get Redis client."""
    global redis_client
    if redis_client is None:
        redis_client = redis.from_url(
            settings.redis_url_computed,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=settings.redis_connect_timeout,
            socket_timeout=settings.redis_command_timeout,
        )
    return redis_client


async def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


async def close_db():
    """Close database connections."""
    if redis_client:
        await redis_client.close()
