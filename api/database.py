from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json
from pathlib import Path

# Create SQLite database in api directory
DATABASE_URL = f"sqlite:///{Path(__file__).parent}/chatdev.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, index=True)  # PENDING, RUNNING, COMPLETED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    request_data = Column(JSON)
    result_path = Column(String, nullable=True)
    error_message = Column(String, nullable=True)

# Create tables
Base.metadata.create_all(bind=engine)