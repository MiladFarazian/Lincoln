import os

from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, case, nulls_last

from .database import engine, Base, get_db
from .models import Job, Swipe, Search, ModelMetadata
from .schemas import JobOut, SwipeIn, SwipeOut, ScrapeIn, ScrapeOut, ScrapeStatus, ModelStatus, StatsOut

app = FastAPI(title="Lincoln", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# --- Scraping ---

@app.post("/api/scrape", response_model=ScrapeOut)
async def scrape_jobs(body: ScrapeIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from .scraper import run_scrape
    search = Search(keywords=body.keywords, location=body.location)
    db.add(search)
    db.commit()
    db.refresh(search)
    background_tasks.add_task(
        run_scrape, search.id, body.keywords, body.location,
        body.max_days, body.experience,
    )
    return ScrapeOut(search_id=search.id, jobs_found=0)


@app.get("/api/scrape/{search_id}/status", response_model=ScrapeStatus)
def get_scrape_status(search_id: int, db: Session = Depends(get_db)):
    search = db.query(Search).filter(Search.id == search_id).first()
    if not search:
        raise HTTPException(status_code=404, detail="Search not found")
    return ScrapeStatus(
        search_id=search.id,
        status=search.status or "pending",
        progress=search.progress or 0,
        message=search.status_message or "",
        jobs_found=search.jobs_found or 0,
    )


# --- Jobs ---

@app.get("/api/jobs/next", response_model=list[JobOut])
def get_next_jobs(limit: int = Query(default=10, le=50), db: Session = Depends(get_db)):
    jobs = (
        db.query(Job)
        .filter(Job.swiped == False)
        .order_by(nulls_last(Job.score.desc()), Job.date_scraped.desc())
        .limit(limit)
        .all()
    )
    return jobs


# --- Swipes ---

@app.post("/api/swipe", response_model=SwipeOut)
def record_swipe(body: SwipeIn, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == body.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    swipe = Swipe(job_id=body.job_id, direction=body.direction)
    db.add(swipe)
    job.swiped = True
    db.commit()
    db.refresh(swipe)

    # Auto-retrain after every 20 new swipes
    total_swipes = db.query(Swipe).count()
    last_model = db.query(ModelMetadata).order_by(ModelMetadata.id.desc()).first()
    last_trained_on = last_model.num_samples if last_model else 0
    if total_swipes - last_trained_on >= 20:
        background_tasks.add_task(_retrain_and_score)

    return swipe


@app.delete("/api/swipe/{swipe_id}")
def undo_swipe(swipe_id: int, db: Session = Depends(get_db)):
    swipe = db.query(Swipe).filter(Swipe.id == swipe_id).first()
    if not swipe:
        raise HTTPException(status_code=404, detail="Swipe not found")
    job = db.query(Job).filter(Job.id == swipe.job_id).first()
    if job:
        job.swiped = False
        job.score = None
    db.delete(swipe)
    db.commit()
    return {"status": "ok"}


# --- Saved Jobs ---

@app.get("/api/saved", response_model=list[JobOut])
def get_saved_jobs(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(Job)
        .join(Swipe, Swipe.job_id == Job.id)
        .filter(Swipe.direction == "right")
        .order_by(Swipe.timestamp.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return jobs


# --- Model ---

@app.post("/api/model/retrain", response_model=ModelStatus)
def retrain_model(db: Session = Depends(get_db)):
    from .ml import JobRecommender
    recommender = JobRecommender()
    result = recommender.train(db)
    if result.get("status") == "insufficient_data":
        raise HTTPException(status_code=400, detail=f"Need at least 20 swipes, have {result['count']}")
    recommender.predict_scores(db)
    return ModelStatus(**result)


@app.get("/api/model/status", response_model=ModelStatus)
def get_model_status(db: Session = Depends(get_db)):
    meta = db.query(ModelMetadata).order_by(ModelMetadata.id.desc()).first()
    if not meta:
        return ModelStatus()
    return ModelStatus(
        trained_at=meta.trained_at,
        num_samples=meta.num_samples,
        accuracy=meta.accuracy,
        precision_right=meta.precision_right,
        recall_right=meta.recall_right,
    )


# --- Stats ---

@app.get("/api/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    total_jobs = db.query(Job).count()
    total_swipes = db.query(Swipe).count()
    right_swipes = db.query(Swipe).filter(Swipe.direction == "right").count()
    left_swipes = db.query(Swipe).filter(Swipe.direction == "left").count()

    last_model = db.query(ModelMetadata).order_by(ModelMetadata.id.desc()).first()
    model_accuracy = last_model.accuracy if last_model else None
    last_trained_on = last_model.num_samples if last_model else 0
    swipes_until_retrain = max(0, 20 - (total_swipes - last_trained_on))

    return StatsOut(
        total_jobs=total_jobs,
        total_swipes=total_swipes,
        right_swipes=right_swipes,
        left_swipes=left_swipes,
        model_accuracy=model_accuracy,
        swipes_until_retrain=swipes_until_retrain,
    )


# --- Admin ---

@app.delete("/api/jobs/all")
def clear_all_jobs(db: Session = Depends(get_db)):
    """Clear all jobs and swipes to start fresh."""
    db.query(Swipe).delete()
    db.query(Job).delete()
    db.commit()
    return {"status": "ok", "message": "All jobs and swipes cleared"}


# --- Helpers ---

def _retrain_and_score():
    from .ml import JobRecommender
    from .database import SessionLocal
    db = SessionLocal()
    try:
        recommender = JobRecommender()
        recommender.train(db)
        recommender.predict_scores(db)
    finally:
        db.close()
