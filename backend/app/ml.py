"""ML recommendation model — TF-IDF + Logistic Regression."""

import os
import pickle
import logging
from datetime import datetime, timezone

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score
from sqlalchemy.orm import Session

from .models import Job, Swipe, ModelMetadata

logger = logging.getLogger(__name__)

MODEL_DIR = os.getenv("MODEL_DIR", "models/")
VECTORIZER_PATH = os.path.join(MODEL_DIR, "vectorizer.pkl")
CLASSIFIER_PATH = os.path.join(MODEL_DIR, "classifier.pkl")
MIN_SAMPLES = 20


class JobRecommender:
    def __init__(self):
        os.makedirs(MODEL_DIR, exist_ok=True)
        self.vectorizer = None
        self.model = None
        self._load()

    def _load(self):
        try:
            with open(VECTORIZER_PATH, "rb") as f:
                self.vectorizer = pickle.load(f)
            with open(CLASSIFIER_PATH, "rb") as f:
                self.model = pickle.load(f)
            logger.info("Loaded existing model")
        except FileNotFoundError:
            logger.info("No existing model found")

    def _save(self):
        with open(VECTORIZER_PATH, "wb") as f:
            pickle.dump(self.vectorizer, f)
        with open(CLASSIFIER_PATH, "wb") as f:
            pickle.dump(self.model, f)

    def _build_text(self, title: str, description: str | None) -> str:
        parts = [title or ""]
        if description:
            parts.append(description)
        return " ".join(parts)

    def train(self, db: Session) -> dict:
        # Gather training data from swipes
        swipes = (
            db.query(Swipe, Job)
            .join(Job, Swipe.job_id == Job.id)
            .all()
        )

        if len(swipes) < MIN_SAMPLES:
            return {"status": "insufficient_data", "count": len(swipes)}

        texts = []
        labels = []
        for swipe, job in swipes:
            text = self._build_text(job.title, job.description)
            texts.append(text)
            labels.append(1 if swipe.direction == "right" else 0)

        # TF-IDF vectorization
        self.vectorizer = TfidfVectorizer(
            max_features=5000,
            stop_words="english",
            ngram_range=(1, 2),
        )
        X = self.vectorizer.fit_transform(texts)
        y = labels

        # Train/test split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )

        # Train logistic regression
        self.model = LogisticRegression(
            class_weight="balanced",
            max_iter=1000,
            random_state=42,
        )
        self.model.fit(X_train, y_train)

        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)

        # Save model artifacts
        self._save()

        # Record metadata
        meta = ModelMetadata(
            trained_at=datetime.now(timezone.utc),
            num_samples=len(swipes),
            accuracy=round(accuracy, 4),
            precision_right=round(precision, 4),
            recall_right=round(recall, 4),
        )
        db.add(meta)
        db.commit()

        logger.info(f"Model trained: accuracy={accuracy:.3f}, precision={precision:.3f}, recall={recall:.3f}")

        return {
            "trained_at": meta.trained_at,
            "num_samples": meta.num_samples,
            "accuracy": meta.accuracy,
            "precision_right": meta.precision_right,
            "recall_right": meta.recall_right,
        }

    def predict_scores(self, db: Session) -> int:
        if self.model is None or self.vectorizer is None:
            return 0

        jobs = db.query(Job).filter(Job.swiped == False).all()
        if not jobs:
            return 0

        texts = [self._build_text(j.title, j.description) for j in jobs]
        X = self.vectorizer.transform(texts)
        scores = self.model.predict_proba(X)[:, 1]

        for job, score in zip(jobs, scores):
            job.score = round(float(score), 4)

        db.commit()
        logger.info(f"Scored {len(jobs)} jobs")
        return len(jobs)

    def score_single(self, title: str, description: str | None) -> float | None:
        if self.model is None or self.vectorizer is None:
            return None
        text = self._build_text(title, description)
        X = self.vectorizer.transform([text])
        return round(float(self.model.predict_proba(X)[0, 1]), 4)
