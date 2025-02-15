from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sodav.db")

# Configure engine with appropriate pooling and concurrency settings
if DATABASE_URL.startswith("sqlite"):
    # SQLite specific settings
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30
        },
        pool_size=20,
        max_overflow=0,
        poolclass=QueuePool,
        pool_pre_ping=True,
        pool_recycle=3600
    )
else:
    # PostgreSQL or other database settings
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_recycle=3600,
        poolclass=QueuePool
    )

# Optimize SQLite performance
def optimize_sqlite(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Use Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")  # Reduce synchronization
    cursor.execute("PRAGMA cache_size=-64000")  # Set cache size to 64MB
    cursor.execute("PRAGMA temp_store=MEMORY")  # Store temp tables in memory
    cursor.execute("PRAGMA mmap_size=268435456")  # Memory-mapped I/O, 256MB
    cursor.close()

# Create SessionLocal class with optimized settings
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # Prevent unnecessary database hits
)

# Create Base class
Base = declarative_base()

# Dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
