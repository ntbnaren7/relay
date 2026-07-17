"""Database engine and asynchronous session factory management."""

from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from relay.adapters.storage.models import Base


def get_db_url(db_path: Path | str | None = None) -> str:
    """Return an async SQLite database connection URL."""
    if not db_path:
        default_dir = Path.home() / ".relay" / "data"
        default_dir.mkdir(parents=True, exist_ok=True)
        db_path = default_dir / "relay.db"
    if str(db_path) == ":memory:":
        return "sqlite+aiosqlite:///:memory:"
    return f"sqlite+aiosqlite:///{db_path}"


def create_engine_and_session(db_url: str | None = None) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Initialize async SQLAlchemy engine and session factory."""
    url = db_url or get_db_url()
    engine = create_async_engine(url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    return engine, session_factory


async def init_db(engine: AsyncEngine) -> None:
    """Create all database tables cleanly."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
