"""Job scraper using free APIs — RemoteOK + keyword filtering."""

import re
import logging
import time
from typing import Optional

import requests
from bs4 import BeautifulSoup

from .database import SessionLocal
from .models import Job, Search

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


def _matches_keywords(job: dict, keywords: str) -> bool:
    """Check if a job matches the search keywords (case-insensitive)."""
    terms = keywords.lower().split()
    searchable = " ".join([
        job.get("title", ""),
        job.get("company", ""),
        job.get("description", ""),
        job.get("location", ""),
        " ".join(job.get("tags", [])),
    ]).lower()
    # Match if ANY keyword appears in the job
    return any(term in searchable for term in terms)


def _clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not text:
        return ""
    cleaned = BeautifulSoup(text, "html.parser").get_text(separator="\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned.strip())
    return cleaned


def _scrape_remoteok(keywords: str) -> list[dict]:
    """Fetch jobs from RemoteOK API and filter by keywords."""
    try:
        resp = requests.get(
            "https://remoteok.com/api",
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"RemoteOK returned {resp.status_code}")
            return []

        data = resp.json()
        jobs = []

        for item in data:
            if not item.get("position"):
                continue

            job = {
                "title": item.get("position", ""),
                "company": item.get("company", ""),
                "location": item.get("location", "Remote"),
                "url": item.get("url", ""),
                "date_posted": item.get("date", ""),
                "salary": "",
                "description": _clean_html(item.get("description", "")),
                "tags": item.get("tags", []),
            }

            # Build salary string from min/max
            sal_min = item.get("salary_min")
            sal_max = item.get("salary_max")
            if sal_min and sal_max:
                job["salary"] = f"${int(sal_min):,} - ${int(sal_max):,}"
            elif sal_min:
                job["salary"] = f"${int(sal_min):,}+"

            if _matches_keywords(job, keywords):
                jobs.append(job)

        logger.info(f"RemoteOK: {len(jobs)} jobs matching '{keywords}' (from {len(data)} total)")
        return jobs

    except Exception as e:
        logger.error(f"RemoteOK failed: {e}")
        return []


def _scrape_linkedin_guest(keywords: str, location: str) -> list[dict]:
    """Try LinkedIn's guest API as a secondary source."""
    try:
        from urllib.parse import quote_plus
        url = f"https://www.linkedin.com/jobs-guest/api/seeJobs?keywords={quote_plus(keywords)}&location={quote_plus(location or 'United States')}&start=0"

        resp = requests.get(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        }, timeout=15)

        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []

        for card in soup.find_all("div", class_="base-card"):
            try:
                title_el = card.find("h3")
                company_el = card.find("h4")
                location_el = card.find("span", class_="job-search-card__location")
                link_el = card.find("a", href=True)
                time_el = card.find("time")

                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                job_url = link_el["href"].split("?")[0] if link_el else None

                jobs.append({
                    "title": title,
                    "company": company_el.get_text(strip=True) if company_el else None,
                    "location": location_el.get_text(strip=True) if location_el else None,
                    "url": job_url,
                    "date_posted": time_el.get("datetime") if time_el else None,
                    "salary": None,
                    "description": None,
                })
            except Exception:
                continue

        logger.info(f"LinkedIn guest: {len(jobs)} jobs for '{keywords}'")
        return jobs

    except Exception as e:
        logger.error(f"LinkedIn guest failed: {e}")
        return []


def scrape_jobs(keywords: str, location: str = "") -> list[dict]:
    """Main entry point. Combines results from multiple sources."""
    all_jobs = []

    # Primary: RemoteOK (most reliable)
    all_jobs.extend(_scrape_remoteok(keywords))

    # Secondary: LinkedIn guest API (may or may not work)
    linkedin_jobs = _scrape_linkedin_guest(keywords, location)
    all_jobs.extend(linkedin_jobs)

    # Deduplicate by URL
    seen = set()
    unique = []
    for job in all_jobs:
        url = job.get("url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(job)
        elif not url:
            unique.append(job)

    logger.info(f"Total unique jobs: {len(unique)} for '{keywords}'")
    return unique


def _filter_by_experience(jobs: list[dict], experience: str) -> list[dict]:
    """Filter jobs by experience level based on title keywords."""
    if not experience:
        return jobs

    # Keywords that indicate senior/staff roles
    senior_keywords = ["senior", "sr.", "sr ", "staff", "principal", "lead", "director", "vp ", "head of", "manager"]
    entry_keywords = ["intern", "junior", "jr.", "jr ", "entry", "associate", "graduate", "new grad"]

    filtered = []
    for job in jobs:
        title_lower = job.get("title", "").lower()

        if experience == "entry":
            # Exclude senior/staff roles
            if any(kw in title_lower for kw in senior_keywords):
                continue
        elif experience == "mid":
            # Exclude explicitly senior/staff AND entry-level roles
            if any(kw in title_lower for kw in senior_keywords + entry_keywords):
                continue
        elif experience == "senior":
            # Exclude entry-level and staff+ roles
            staff_keywords = ["staff", "principal", "director", "vp ", "head of"]
            if any(kw in title_lower for kw in entry_keywords + staff_keywords):
                continue
        elif experience == "staff":
            # Exclude entry/mid roles (keep senior and above)
            if any(kw in title_lower for kw in entry_keywords):
                continue

        filtered.append(job)

    logger.info(f"Experience filter '{experience}': {len(filtered)}/{len(jobs)} jobs kept")
    return filtered


def _filter_by_date(jobs: list[dict], max_days: Optional[int]) -> list[dict]:
    """Filter jobs by posting date."""
    if not max_days:
        return jobs

    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
    filtered = []

    for job in jobs:
        date_str = job.get("date_posted")
        if not date_str:
            # Keep jobs with no date (can't filter them)
            filtered.append(job)
            continue

        try:
            # Try ISO format (RemoteOK uses this)
            posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            if posted >= cutoff:
                filtered.append(job)
        except (ValueError, TypeError):
            # Can't parse date, keep the job
            filtered.append(job)

    logger.info(f"Date filter (last {max_days} days): {len(filtered)}/{len(jobs)} jobs kept")
    return filtered


def run_scrape(search_id: int, keywords: str, location: str,
               max_days: Optional[int] = None, experience: str = "mid"):
    """Background task entry point."""
    db = SessionLocal()
    try:
        jobs = scrape_jobs(keywords, location)

        # Apply filters
        jobs = _filter_by_experience(jobs, experience)
        jobs = _filter_by_date(jobs, max_days)

        inserted = 0
        for job_data in jobs:
            url = job_data.get("url")
            if url:
                existing = db.query(Job).filter(Job.url == url).first()
                if existing:
                    continue

            job = Job(
                title=job_data["title"],
                company=job_data.get("company"),
                location=job_data.get("location"),
                description=job_data.get("description"),
                url=url,
                salary=job_data.get("salary") or None,
                date_posted=job_data.get("date_posted"),
            )
            db.add(job)
            inserted += 1

        search = db.query(Search).filter(Search.id == search_id).first()
        if search:
            search.jobs_found = inserted

        db.commit()

        # Score new jobs if model exists
        try:
            from .ml import JobRecommender
            recommender = JobRecommender()
            if recommender.model is not None:
                recommender.predict_scores(db)
        except Exception:
            pass

        logger.info(f"Inserted {inserted} new jobs for search {search_id}")
    except Exception as e:
        logger.error(f"Scrape failed for search {search_id}: {e}")
    finally:
        db.close()
