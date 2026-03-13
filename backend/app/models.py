from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    company = Column(String(256))
    location = Column(String(256))
    description = Column(Text)
    url = Column(String(512), unique=True)
    salary = Column(String(128), nullable=True)
    date_posted = Column(String(64))
    date_scraped = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    score = Column(Float, nullable=True)
    swiped = Column(Boolean, default=False)

    swipes = relationship("Swipe", back_populates="job")


class Swipe(Base):
    __tablename__ = "swipes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    direction = Column(String(8), nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    job = relationship("Job", back_populates="swipes")


class Search(Base):
    __tablename__ = "searches"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keywords = Column(String(256), nullable=False)
    location = Column(String(256), default="")
    date_run = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    jobs_found = Column(Integer, default=0)
    status = Column(String(32), default="pending")  # pending, scraping, filtering, scoring, done, error
    progress = Column(Integer, default=0)  # 0-100
    status_message = Column(String(256), default="")


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    num_samples = Column(Integer)
    accuracy = Column(Float)
    precision_right = Column(Float)
    recall_right = Column(Float)
