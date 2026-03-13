"""LinkedIn job search scraper using Playwright."""

import asyncio
import random
import re
import logging
from urllib.parse import quote_plus
from typing import Optional

from playwright.async_api import async_playwright, Page
from sqlalchemy.orm import Session

from . import scraper_config as cfg
from .database import SessionLocal
from .models import Job, Search

logger = logging.getLogger(__name__)


class LinkedInScraper:
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _build_search_url(self, keywords: str, location: str, page: int) -> str:
        base = "https://www.linkedin.com/jobs/search/"
        params = f"?keywords={quote_plus(keywords)}&start={page * cfg.JOBS_PER_PAGE}"
        if location:
            params += f"&location={quote_plus(location)}"
        return base + params

    async def _random_delay(self, min_s: float = cfg.DELAY_MIN, max_s: float = cfg.DELAY_MAX):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _parse_job_cards(self, page: Page) -> list[dict]:
        jobs = []
        try:
            await page.wait_for_selector(cfg.SELECTORS["job_card"], timeout=15000)
        except Exception:
            logger.warning("No job cards found on page")
            return jobs

        cards = await page.query_selector_all(cfg.SELECTORS["job_card"])
        for card in cards:
            try:
                title_el = await card.query_selector(cfg.SELECTORS["title"])
                company_el = await card.query_selector(cfg.SELECTORS["company"])
                location_el = await card.query_selector(cfg.SELECTORS["location"])
                link_el = await card.query_selector(cfg.SELECTORS["link"])
                date_el = await card.query_selector(cfg.SELECTORS["date"])
                salary_el = await card.query_selector(cfg.SELECTORS["salary"])

                title = (await title_el.inner_text()).strip() if title_el else None
                company = (await company_el.inner_text()).strip() if company_el else None
                location = (await location_el.inner_text()).strip() if location_el else None
                url = await link_el.get_attribute("href") if link_el else None
                date_posted = await date_el.get_attribute(cfg.SELECTORS["date_attr"]) if date_el else None
                salary = (await salary_el.inner_text()).strip() if salary_el else None

                if title and url:
                    # Clean URL — remove tracking params
                    url = url.split("?")[0] if url else url
                    jobs.append({
                        "title": title,
                        "company": company,
                        "location": location,
                        "url": url,
                        "date_posted": date_posted,
                        "salary": salary,
                    })
            except Exception as e:
                logger.debug(f"Error parsing card: {e}")
                continue
        return jobs

    async def _fetch_description(self, page: Page, url: str) -> Optional[str]:
        try:
            await page.goto(url, wait_until="domcontentloaded")
            await self._random_delay(cfg.DETAIL_DELAY_MIN, cfg.DETAIL_DELAY_MAX)
            desc_el = await page.wait_for_selector(cfg.SELECTORS["description"], timeout=10000)
            if desc_el:
                text = await desc_el.inner_text()
                # Normalize whitespace
                text = re.sub(r"\n{3,}", "\n\n", text.strip())
                return text
        except Exception as e:
            logger.debug(f"Error fetching description for {url}: {e}")
        return None

    async def scrape_jobs(
        self, keywords: str, location: str = "", max_pages: int = cfg.MAX_PAGES
    ) -> list[dict]:
        all_jobs = []
        seen_urls = set()

        async with async_playwright() as p:
            ua = random.choice(cfg.USER_AGENTS)
            vp = random.choice(cfg.VIEWPORTS)

            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            context = await browser.new_context(
                user_agent=ua,
                viewport=vp,
            )
            page = await context.new_page()

            # Scrape search result pages
            for page_num in range(max_pages):
                url = self._build_search_url(keywords, location, page_num)
                logger.info(f"Scraping page {page_num + 1}: {url}")

                try:
                    await page.goto(url, wait_until="domcontentloaded")
                    await self._random_delay()

                    # Scroll down to load more results
                    for _ in range(3):
                        await page.evaluate("window.scrollBy(0, 800)")
                        await asyncio.sleep(0.5)

                    cards = await self._parse_job_cards(page)
                    if not cards:
                        logger.info("No more results, stopping pagination")
                        break

                    for job in cards:
                        if job["url"] not in seen_urls:
                            seen_urls.add(job["url"])
                            all_jobs.append(job)

                except Exception as e:
                    logger.error(f"Error on page {page_num + 1}: {e}")
                    break

                await self._random_delay()

            # Fetch full descriptions for each job
            for job in all_jobs:
                if job.get("url"):
                    description = await self._fetch_description(page, job["url"])
                    job["description"] = description

            await browser.close()

        logger.info(f"Scraped {len(all_jobs)} jobs for '{keywords}'")
        return all_jobs


def run_scrape(search_id: int, keywords: str, location: str):
    """Background task entry point — runs the async scraper and saves results to DB."""
    db = SessionLocal()
    try:
        scraper = LinkedInScraper()
        jobs = asyncio.run(scraper.scrape_jobs(keywords, location))

        inserted = 0
        for job_data in jobs:
            existing = db.query(Job).filter(Job.url == job_data["url"]).first()
            if existing:
                continue
            job = Job(
                title=job_data["title"],
                company=job_data.get("company"),
                location=job_data.get("location"),
                description=job_data.get("description"),
                url=job_data["url"],
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
