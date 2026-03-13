"""LinkedIn job search scraper — requests + BeautifulSoup approach with API fallback."""

import asyncio
import random
import re
import logging
import time
from urllib.parse import quote_plus
from typing import Optional

import requests
from bs4 import BeautifulSoup

from . import scraper_config as cfg
from .database import SessionLocal
from .models import Job, Search

logger = logging.getLogger(__name__)


class LinkedInScraper:
    """Scrape LinkedIn's public job search pages using requests + BeautifulSoup.
    Falls back to a free jobs API if LinkedIn blocks the request."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": random.choice(cfg.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })

    def _build_search_url(self, keywords: str, location: str, start: int) -> str:
        base = "https://www.linkedin.com/jobs-guest/api/seeJobs"
        params = f"?keywords={quote_plus(keywords)}&start={start}"
        if location:
            params += f"&location={quote_plus(location)}"
        return base + params

    def _scrape_linkedin(self, keywords: str, location: str, max_pages: int) -> list[dict]:
        """Try LinkedIn's guest job search API (returns HTML fragments)."""
        all_jobs = []
        seen_urls = set()

        for page_num in range(max_pages):
            start = page_num * cfg.JOBS_PER_PAGE
            url = self._build_search_url(keywords, location, start)
            logger.info(f"Fetching LinkedIn page {page_num + 1}: {url}")

            try:
                resp = self.session.get(url, timeout=15)
                if resp.status_code != 200:
                    logger.warning(f"LinkedIn returned {resp.status_code}, stopping")
                    break

                soup = BeautifulSoup(resp.text, "html.parser")
                cards = soup.find_all("li")

                if not cards:
                    logger.info("No more results from LinkedIn")
                    break

                for card in cards:
                    try:
                        title_el = card.find("h3", class_="base-search-card__title")
                        company_el = card.find("h4", class_="base-search-card__subtitle")
                        location_el = card.find("span", class_="job-search-card__location")
                        link_el = card.find("a", class_="base-card__full-link")
                        time_el = card.find("time")
                        salary_el = card.find("span", class_="job-search-card__salary-info")

                        title = title_el.get_text(strip=True) if title_el else None
                        company = company_el.get_text(strip=True) if company_el else None
                        loc = location_el.get_text(strip=True) if location_el else None
                        job_url = link_el["href"].split("?")[0] if link_el and link_el.get("href") else None
                        date_posted = time_el.get("datetime") if time_el else None
                        salary = salary_el.get_text(strip=True) if salary_el else None

                        if title and job_url and job_url not in seen_urls:
                            seen_urls.add(job_url)
                            all_jobs.append({
                                "title": title,
                                "company": company,
                                "location": loc,
                                "url": job_url,
                                "date_posted": date_posted,
                                "salary": salary,
                                "description": None,
                            })
                    except Exception as e:
                        logger.debug(f"Error parsing card: {e}")
                        continue

                # Rate limit
                time.sleep(random.uniform(cfg.DELAY_MIN, cfg.DELAY_MAX))

            except Exception as e:
                logger.error(f"Error fetching LinkedIn page {page_num + 1}: {e}")
                break

        # Fetch descriptions for each job
        for job in all_jobs:
            if job.get("url"):
                job["description"] = self._fetch_description(job["url"])
                time.sleep(random.uniform(cfg.DETAIL_DELAY_MIN, cfg.DETAIL_DELAY_MAX))

        return all_jobs

    def _fetch_description(self, url: str) -> Optional[str]:
        """Fetch full job description from the job detail page."""
        try:
            resp = self.session.get(url, timeout=15)
            if resp.status_code != 200:
                return None
            soup = BeautifulSoup(resp.text, "html.parser")
            desc_el = soup.find("div", class_="show-more-less-html__markup")
            if desc_el:
                text = desc_el.get_text(separator="\n", strip=True)
                text = re.sub(r"\n{3,}", "\n\n", text)
                return text
        except Exception as e:
            logger.debug(f"Error fetching description for {url}: {e}")
        return None

    def _scrape_jooble_fallback(self, keywords: str, location: str) -> list[dict]:
        """Fallback: use Jooble's free API for job results."""
        try:
            resp = requests.post(
                "https://jooble.org/api/",
                json={"keywords": keywords, "location": location or "United States"},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            jobs = []
            for item in data.get("jobs", []):
                # Clean HTML from snippet
                snippet = item.get("snippet", "")
                if snippet:
                    snippet = BeautifulSoup(snippet, "html.parser").get_text()

                jobs.append({
                    "title": item.get("title", "Unknown"),
                    "company": item.get("company", None),
                    "location": item.get("location", None),
                    "url": item.get("link", None),
                    "date_posted": item.get("updated", None),
                    "salary": item.get("salary", None),
                    "description": snippet or None,
                })
            return jobs
        except Exception as e:
            logger.error(f"Jooble fallback failed: {e}")
            return []

    def scrape_jobs(self, keywords: str, location: str = "", max_pages: int = cfg.MAX_PAGES) -> list[dict]:
        """Main entry point. Try LinkedIn first, fall back to Jooble."""
        jobs = self._scrape_linkedin(keywords, location, max_pages)

        if not jobs:
            logger.info("LinkedIn returned 0 results, trying Jooble fallback")
            jobs = self._scrape_jooble_fallback(keywords, location)

        logger.info(f"Total scraped: {len(jobs)} jobs for '{keywords}'")
        return jobs


def run_scrape(search_id: int, keywords: str, location: str):
    """Background task entry point."""
    db = SessionLocal()
    try:
        scraper = LinkedInScraper()
        jobs = scraper.scrape_jobs(keywords, location)

        inserted = 0
        for job_data in jobs:
            url = job_data.get("url")
            if not url:
                continue
            existing = db.query(Job).filter(Job.url == url).first()
            if existing:
                continue
            job = Job(
                title=job_data["title"],
                company=job_data.get("company"),
                location=job_data.get("location"),
                description=job_data.get("description"),
                url=url,
                salary=job_data.get("salary"),
                date_posted=job_data.get("date_posted"),
            )
            db.add(job)
            inserted += 1

        # Update search record
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
