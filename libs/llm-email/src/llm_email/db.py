"""Database initialization and teardown for Tortoise ORM."""

import os

from tortoise import Tortoise

from llm_email.config import DATA_DIR, DB_URL
from llm_email.logger import log


async def init_db(db_url: str | None = None):
    """Initialize Tortoise ORM with SQLite. Creates DB file automatically."""
    os.makedirs(DATA_DIR, exist_ok=True)
    url = db_url or DB_URL
    log.debug("Initializing database: %s", url)
    await Tortoise.init(
        db_url=url,
        modules={"models": ["llm_email.models"]},
    )
    await Tortoise.generate_schemas()
    log.debug("Database ready")


async def close_db():
    """Close all Tortoise connections."""
    await Tortoise.close_connections()
