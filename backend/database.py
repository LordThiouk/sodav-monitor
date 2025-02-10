from sqlalchemy import create_engine, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from dotenv import load_dotenv
import os

load_dotenv()

# Get database URL from environment variable or use SQLite as default
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/sodav_monitor.db")

# Create SQLAlchemy engine with optimized settings
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args={
        "check_same_thread": False,  # Required for SQLite
        "timeout": 30  # SQLite timeout in seconds
    }
)

# Optimize SQLite performance
@event.listens_for(engine, "connect")
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
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
