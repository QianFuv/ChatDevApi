from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import json
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger("chatdev-api.database")

# Create SQLite database in api directory
DATABASE_URL = f"sqlite:///{Path(__file__).parent}/chatdev.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Task(Base):
    """
    Database model for tracking ChatDev generation tasks
    """
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String(20), index=True)  # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    request_data = Column(JSON)
    result_path = Column(String(255), nullable=True)
    apk_path = Column(String(255), nullable=True)  # New field for APK file path
    build_apk = Column(Boolean, default=False)  # New field to indicate if APK build was requested
    error_message = Column(Text, nullable=True)
    pid = Column(Integer, nullable=True)  # Process ID for task cancellation

    # Add indices for efficient queries
    __table_args__ = (
        Index('idx_status_created', status, created_at),
    )

    def to_dict(self):
        """Convert task to dictionary"""
        return {
            "id": self.id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "request_data": self.request_data,
            "result_path": self.result_path,
            "apk_path": self.apk_path,
            "build_apk": self.build_apk,
            "error_message": self.error_message,
            "pid": self.pid
        }

# Dependency to get DB session
def get_db():
    """
    FastAPI dependency that provides a database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Initialize database
def init_db():
    """
    Initialize the database with all defined tables
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}")
        raise

# Initialize the database
init_db()