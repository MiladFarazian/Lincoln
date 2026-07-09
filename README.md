# Lincoln — swipe-based job search

Tinder for jobs: swipe through scraped postings, and a recommender learns your taste from every swipe — no forms, no filters, just implicit feedback.

**Live loop:** scrape postings → swipe left/right → after every 20 new swipes, a background task retrains a TF-IDF + Logistic Regression model on your swipe history → the feed re-ranks toward what you actually like. Right-swiped jobs can generate a tailored resume draft via the Anthropic API.

## Architecture

```
frontend/   Next.js + TypeScript — swipe UI
backend/    FastAPI + SQLAlchemy (Postgres) — API, scraper, ML, resume crafting
  app/scraper.py         job-board scraper
  app/ml.py              JobRecommender: TfidfVectorizer + LogisticRegression
  app/main.py            API routes; auto-retrain every 20 swipes (background task)
  app/resume_crafter.py  Anthropic-API resume tailoring for saved jobs
```

- The model trains once ≥20 labeled swipes exist, then retrains automatically every 20 new swipes (`POST /api/model/retrain` forces it).
- Model artifacts (vectorizer + classifier) are pickled to `models/` and reloaded on boot.
- Dockerized; deployed to Railway (`backend/railway.json`).

## Run it

```bash
# backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload        # needs DATABASE_URL and ANTHROPIC_API_KEY in .env

# frontend
cd frontend
npm install && npm run dev
```

Built by [Milad Farazian](https://miladfarazian.com) — more at [github.com/miladfarazian](https://github.com/miladfarazian).
