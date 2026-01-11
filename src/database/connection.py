"""Database connection management."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# Will be initialized by settings
engine = None
SessionLocal = None


def init_database(database_url: str, echo: bool = False):
    """Initialize database engine and session factory.

    Args:
        database_url: PostgreSQL connection string
        echo: Whether to log SQL queries
    """
    global engine, SessionLocal

    engine = create_engine(
        database_url,
        echo=echo,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine
    )


def get_db_session() -> Session:
    """Get a database session.

    Returns:
        SQLAlchemy session
    """
    if SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    return SessionLocal()


@contextmanager
def get_db_context():
    """Context manager for database sessions.

    Usage:
        with get_db_context() as db:
            db.query(Model).all()
    """
    db = get_db_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
