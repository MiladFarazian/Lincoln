from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel


class JobOut(BaseModel):
    id: int
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    salary: Optional[str] = None
    date_posted: Optional[str] = None
    score: Optional[float] = None

    model_config = {"from_attributes": True}


class SwipeIn(BaseModel):
    job_id: int
    direction: Literal["left", "right"]


class SwipeOut(BaseModel):
    id: int
    job_id: int
    direction: str
    timestamp: datetime

    model_config = {"from_attributes": True}


class ScrapeIn(BaseModel):
    keywords: str
    location: str = ""
    max_days: Optional[int] = None
    experience: str = "mid"


class ScrapeOut(BaseModel):
    search_id: int
    jobs_found: int


class ModelStatus(BaseModel):
    trained_at: Optional[datetime] = None
    num_samples: Optional[int] = None
    accuracy: Optional[float] = None
    precision_right: Optional[float] = None
    recall_right: Optional[float] = None


class StatsOut(BaseModel):
    model_config = {"protected_namespaces": ()}

    total_jobs: int
    total_swipes: int
    right_swipes: int
    left_swipes: int
    model_accuracy: Optional[float] = None
    swipes_until_retrain: int
