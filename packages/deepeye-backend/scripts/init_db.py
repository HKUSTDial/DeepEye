#!/usr/bin/env python3
"""Initialize database tables using SQLAlchemy metadata.

This script creates all database tables based on SQLAlchemy models.
Simple and straightforward approach for development and early-stage projects.

Usage:
    python scripts/init_db.py
    # or
    uv run python scripts/init_db.py
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.config import settings
from app.db.base import Base
# Import all models to register them with Base.metadata
from app.models.database import (  # noqa: F401
    DatabaseConnection,
    File,
    LLMModel,
    PasswordResetToken,
    User,
    Workflow,
)


async def init_db():
    """Initialize database tables."""
    # Mask password in URL for display
    display_url = settings.DATABASE_URL
    if ":" in display_url and "@" in display_url:
        # Mask password: postgresql://user:password@host -> postgresql://user:***@host
        parts = display_url.split("@")
        if len(parts) == 2:
            auth_part = parts[0].split("://")[-1]
            if ":" in auth_part:
                user = auth_part.split(":")[0]
                display_url = display_url.replace(f":{auth_part.split(':')[1]}", ":***")
    
    print(f"🔗 Connecting to database: {display_url}")
    
    # Create async engine
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
    )
    
    try:
        # Create all tables
        print("📦 Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully!")
        print("\n📊 Created tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"   - {table_name}")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())

