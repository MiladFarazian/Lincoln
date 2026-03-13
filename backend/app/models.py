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
    fingerprint = Column(String(64), index=True)  # hash of normalized title+company for cross-source dedup

    swipes = relationship("Swipe", back_populates="job")


class SwipedFingerprint(Base):
    """Permanent memory of swiped jobs — survives job deletions and re-scrapes."""
    __tablename__ = "swiped_fingerprints"

    id = Column(Integer, primary_key=True, autoincrement=True)
    fingerprint = Column(String(64), unique=True, nullable=False, index=True)
    direction = Column(String(8), nullable=False)  # left or right
    title = Column(String(256))  # for debugging
    company = Column(String(256))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))


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


class UserResume(Base):
    __tablename__ = "user_resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class CraftedResume(Base):
    __tablename__ = "crafted_resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    crafted_content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    job = relationship("Job")


class ModelMetadata(Base):
    __tablename__ = "model_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trained_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    num_samples = Column(Integer)
    accuracy = Column(Float)
    precision_right = Column(Float)
    recall_right = Column(Float)
