"""Job scraper using multiple free APIs and sources."""

import re
import logging
import time
from typing import Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .database import SessionLocal
from .models import Job, Search

logger = logging.getLogger(__name__)

BROWSER_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "application/json",
}


def _matches_keywords(job: dict, keywords: str) -> bool:
    """Check if a job matches the search keywords.

    Strategy:
    - First check if the full phrase appears in the title (best match)
    - Then check if ALL keywords appear in the title
    - Then check if ALL keywords appear across title + tags
    - Single-word searches: match if that word is in the title
    """
    kw_lower = keywords.lower().strip()
    title = job.get("title", "").lower()
    tags = " ".join(job.get("tags", [])).lower()
    title_and_tags = f"{title} {tags}"

    # Full phrase match in title — best signal
    if kw_lower in title:
        return True

    terms = kw_lower.split()

    # Single keyword: must appear in title or tags
    if len(terms) == 1:
        return terms[0] in title_and_tags

    # Multi-keyword: ALL terms must appear in title+tags
    # (not description — too many false positives)
    return all(term in title_and_tags for term in terms)


def _clean_html(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not text:
        return ""
    cleaned = BeautifulSoup(text, "html.parser").get_text(separator="\n")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned.strip())
    return cleaned


# --- Source: RemoteOK ---

def _scrape_remoteok(keywords: str) -> list[dict]:
    """Fetch jobs from RemoteOK API and filter by keywords."""
    try:
        resp = requests.get("https://remoteok.com/api", headers=HEADERS, timeout=15)
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


# --- Source: LinkedIn Guest ---

def _scrape_linkedin_guest(keywords: str, location: str) -> list[dict]:
    """Scrape LinkedIn's guest job search pages (multiple URL patterns, multiple pages)."""
    all_jobs = []

    # Try both the API endpoint and the HTML search page
    url_patterns = [
        "https://www.linkedin.com/jobs-guest/jobs/api/seeJobs?keywords={kw}&location={loc}&start={start}",
        "https://www.linkedin.com/jobs/search?keywords={kw}&location={loc}&start={start}",
    ]

    for pattern in url_patterns:
        for start in [0, 25, 50]:
            try:
                url = pattern.format(
                    kw=quote_plus(keywords),
                    loc=quote_plus(location or "United States"),
                    start=start,
                )

                resp = requests.get(url, headers={
                    "User-Agent": BROWSER_UA,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                }, timeout=15)

                if resp.status_code != 200:
                    logger.warning(f"LinkedIn {pattern[:50]}... start={start} returned {resp.status_code}")
                    break  # If first page fails, skip remaining pages for this pattern

                soup = BeautifulSoup(resp.text, "html.parser")

                # Try multiple card selectors (LinkedIn changes these)
                cards = soup.find_all("div", class_="base-card")
                if not cards:
                    cards = soup.find_all("div", class_="base-search-card")
                if not cards:
                    cards = soup.find_all("li", class_="jobs-search__result-card")

                page_count = 0
                for card in cards:
                    try:
                        title_el = card.find("h3") or card.find("span", class_="sr-only")
                        company_el = card.find("h4") or card.find("a", class_="hidden-nested-link")
                        location_el = card.find("span", class_="job-search-card__location")
                        link_el = card.find("a", href=True)
                        time_el = card.find("time")

                        title = title_el.get_text(strip=True) if title_el else None
                        if not title:
                            continue

                        job_url = link_el["href"].split("?")[0] if link_el else None

                        all_jobs.append({
                            "title": title,
                            "company": company_el.get_text(strip=True) if company_el else None,
                            "location": location_el.get_text(strip=True) if location_el else None,
                            "url": job_url,
                            "date_posted": time_el.get("datetime") if time_el else None,
                            "salary": None,
                            "description": None,
                        })
                        page_count += 1
                    except Exception:
                        continue

                if page_count == 0:
                    break  # No results, skip remaining pages

                time.sleep(1.5)

            except Exception as e:
                logger.error(f"LinkedIn guest failed: {e}")
                break

        if all_jobs:
            break  # Got results from first pattern, skip second

    logger.info(f"LinkedIn guest: {len(all_jobs)} jobs for '{keywords}'")
    return all_jobs


# --- Source: Indeed (HTML scrape) ---

def _scrape_indeed(keywords: str, location: str) -> list[dict]:
    """Scrape Indeed search results page."""
    jobs = []
    try:
        url = (
            f"https://www.indeed.com/jobs"
            f"?q={quote_plus(keywords)}"
            f"&l={quote_plus(location or '')}"
            f"&sort=date"
            f"&fromage=14"
        )

        resp = requests.get(url, headers={
            "User-Agent": BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }, timeout=15)

        if resp.status_code != 200:
            logger.warning(f"Indeed returned {resp.status_code}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")

        # Indeed uses various card selectors
        cards = soup.find_all("div", class_="job_seen_beacon")
        if not cards:
            cards = soup.find_all("div", class_="resultContent")
        if not cards:
            cards = soup.find_all("td", class_="resultContent")

        for card in cards:
            try:
                title_el = card.find("h2", class_="jobTitle") or card.find("a", class_="jcs-JobTitle")
                if not title_el:
                    title_el = card.find("span", attrs={"id": lambda x: x and x.startswith("jobTitle")})

                company_el = card.find("span", attrs={"data-testid": "company-name"})
                if not company_el:
                    company_el = card.find("span", class_="companyName")

                location_el = card.find("div", attrs={"data-testid": "text-location"})
                if not location_el:
                    location_el = card.find("div", class_="companyLocation")

                link_el = card.find("a", href=True)

                title = title_el.get_text(strip=True) if title_el else None
                if not title:
                    continue

                job_url = None
                if link_el and link_el.get("href"):
                    href = link_el["href"]
                    if href.startswith("/"):
                        job_url = f"https://www.indeed.com{href}"
                    elif href.startswith("http"):
                        job_url = href

                salary_el = card.find("div", class_="salary-snippet-container") or card.find("div", attrs={"data-testid": "attribute_snippet_testid"})
                salary = salary_el.get_text(strip=True) if salary_el else None

                jobs.append({
                    "title": title,
                    "company": company_el.get_text(strip=True) if company_el else None,
                    "location": location_el.get_text(strip=True) if location_el else None,
                    "url": job_url,
                    "date_posted": None,
                    "salary": salary,
                    "description": None,
                })
            except Exception:
                continue

        logger.info(f"Indeed: {len(jobs)} jobs for '{keywords}' in '{location}'")

    except Exception as e:
        logger.error(f"Indeed failed: {e}")

    return jobs


# --- Source: Arbeitnow ---

def _scrape_arbeitnow(keywords: str) -> list[dict]:
    """Fetch jobs from Arbeitnow free API."""
    jobs = []
    try:
        resp = requests.get(
            "https://www.arbeitnow.com/api/job-board-api",
            headers=HEADERS,
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning(f"Arbeitnow returned {resp.status_code}")
            return []

        data = resp.json().get("data", [])

        for item in data:
            job = {
                "title": item.get("title", ""),
                "company": item.get("company_name", ""),
                "location": item.get("location", ""),
                "url": item.get("url", ""),
                "date_posted": item.get("created_at", ""),
                "salary": None,
                "description": _clean_html(item.get("description", "")),
                "tags": item.get("tags", []),
            }

            if _matches_keywords(job, keywords):
                jobs.append(job)

        logger.info(f"Arbeitnow: {len(jobs)} jobs matching '{keywords}' (from {len(data)} total)")

    except Exception as e:
        logger.error(f"Arbeitnow failed: {e}")

    return jobs


# --- Source: The Muse ---

def _scrape_themuse(keywords: str, location: str) -> list[dict]:
    """Fetch jobs from The Muse public API (no key needed). Fetches multiple pages."""
    jobs = []
    try:
        base_params = {
            "descending": "true",
        }

        # Map keywords to Muse categories
        kw_lower = keywords.lower()
        if any(t in kw_lower for t in ["software", "engineer", "developer", "backend", "frontend", "fullstack", "full-stack"]):
            base_params["category"] = "Engineering"
        elif "data" in kw_lower:
            base_params["category"] = "Data Science"
        elif "design" in kw_lower:
            base_params["category"] = "Design"
        elif "product" in kw_lower:
            base_params["category"] = "Product"

        # Map location
        if location:
            loc_lower = location.lower()
            if "los angeles" in loc_lower or "la" == loc_lower:
                base_params["location"] = "Los Angeles, CA"
            elif "san francisco" in loc_lower or "sf" in loc_lower:
                base_params["location"] = "San Francisco, CA"
            elif "new york" in loc_lower or "nyc" in loc_lower:
                base_params["location"] = "New York, NY"
            elif "seattle" in loc_lower:
                base_params["location"] = "Seattle, WA"
            else:
                base_params["location"] = location

        # Fetch up to 3 pages
        for page in range(3):
            params = {**base_params, "page": page}
            resp = requests.get(
                "https://www.themuse.com/api/public/jobs",
                params=params,
                headers={"User-Agent": BROWSER_UA},
                timeout=15,
            )

            if resp.status_code != 200:
                break

            data = resp.json()
            results = data.get("results", [])
            if not results:
                break

            for item in results:
                locations = item.get("locations", [])
                loc_str = ", ".join(loc.get("name", "") for loc in locations) if locations else "Unknown"

                desc = item.get("contents", "")
                job = {
                    "title": item.get("name", ""),
                    "company": item.get("company", {}).get("name", ""),
                    "location": loc_str,
                    "url": f"https://www.themuse.com/jobs/{item.get('id', '')}",
                    "date_posted": item.get("publication_date", ""),
                    "salary": None,
                    "description": _clean_html(desc),
                    "tags": [cat.get("name", "") for cat in item.get("categories", [])],
                }

                if _matches_keywords(job, keywords):
                    jobs.append(job)

        logger.info(f"The Muse: {len(jobs)} jobs matching '{keywords}'")

    except Exception as e:
        logger.error(f"The Muse failed: {e}")

    return jobs


# --- Source: Himalayas ---

def _scrape_himalayas(keywords: str) -> list[dict]:
    """Fetch remote jobs from Himalayas.app API."""
    jobs = []
    try:
        resp = requests.get(
            "https://himalayas.app/jobs/api",
            params={"limit": 50},
            headers=HEADERS,
            timeout=15,
        )

        if resp.status_code != 200:
            logger.warning(f"Himalayas returned {resp.status_code}")
            return []

        data = resp.json().get("jobs", [])

        for item in data:
            job = {
                "title": item.get("title", ""),
                "company": item.get("companyName", ""),
                "location": "Remote",
                "url": item.get("applicationLink") or f"https://himalayas.app/jobs/{item.get('slug', '')}",
                "date_posted": item.get("pubDate", ""),
                "salary": None,
                "description": _clean_html(item.get("description", "")),
                "tags": item.get("categories", []),
            }

            sal_min = item.get("minSalary")
            sal_max = item.get("maxSalary")
            if sal_min and sal_max:
                job["salary"] = f"${int(sal_min):,} - ${int(sal_max):,}"
            elif sal_min:
                job["salary"] = f"${int(sal_min):,}+"

            if _matches_keywords(job, keywords):
                jobs.append(job)

        logger.info(f"Himalayas: {len(jobs)} jobs matching '{keywords}' (from {len(data)} total)")

    except Exception as e:
        logger.error(f"Himalayas failed: {e}")

    return jobs


# --- Source: Jobicy ---

def _scrape_jobicy(keywords: str) -> list[dict]:
    """Fetch remote jobs from Jobicy API."""
    jobs = []
    try:
        tag = keywords.lower().replace(" ", "-")
        resp = requests.get(
            "https://jobicy.com/api/v2/remote-jobs",
            params={"count": 50, "tag": tag},
            headers=HEADERS,
            timeout=15,
        )

        if resp.status_code != 200:
            logger.warning(f"Jobicy returned {resp.status_code}")
            return []

        data = resp.json().get("jobs", [])

        for item in data:
            sal_min = item.get("annualSalaryMin")
            sal_max = item.get("annualSalaryMax")
            salary = None
            if sal_min and sal_max:
                salary = f"${int(sal_min):,} - ${int(sal_max):,}"
            elif sal_min:
                salary = f"${int(sal_min):,}+"

            job = {
                "title": item.get("jobTitle", ""),
                "company": item.get("companyName", ""),
                "location": item.get("jobGeo", "Remote"),
                "url": item.get("url", ""),
                "date_posted": item.get("pubDate", ""),
                "salary": salary,
                "description": _clean_html(item.get("jobDescription", "")),
                "tags": [],
            }

            if _matches_keywords(job, keywords):
                jobs.append(job)

        logger.info(f"Jobicy: {len(jobs)} jobs matching '{keywords}' (from {len(data)} total)")

    except Exception as e:
        logger.error(f"Jobicy failed: {e}")

    return jobs


# --- Filters ---

def _filter_by_experience(jobs: list[dict], experience: str) -> list[dict]:
    """Filter jobs by experience level based on title keywords."""
    if not experience:
        return jobs

    senior_keywords = ["senior", "sr.", "sr ", "staff", "principal", "lead", "director", "vp ", "head of", "manager"]
    entry_keywords = ["intern", "junior", "jr.", "jr ", "entry", "associate", "graduate", "new grad"]

    filtered = []
    for job in jobs:
        title_lower = job.get("title", "").lower()

        if experience == "entry":
            if any(kw in title_lower for kw in senior_keywords):
                continue
        elif experience == "mid":
            if any(kw in title_lower for kw in senior_keywords + entry_keywords):
                continue
        elif experience == "senior":
            staff_keywords = ["staff", "principal", "director", "vp ", "head of"]
            if any(kw in title_lower for kw in entry_keywords + staff_keywords):
                continue
        elif experience == "staff":
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
            filtered.append(job)
            continue

        try:
            posted = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            if posted >= cutoff:
                filtered.append(job)
        except (ValueError, TypeError):
            filtered.append(job)

    logger.info(f"Date filter (last {max_days} days): {len(filtered)}/{len(jobs)} jobs kept")
    return filtered


# --- Progress helper ---

def _update_search_progress(db, search_id: int, status: str, progress: int, message: str = ""):
    """Update the search record with current progress."""
    search = db.query(Search).filter(Search.id == search_id).first()
    if search:
        search.status = status
        search.progress = progress
        search.status_message = message
        db.commit()


# --- Main scrape runner ---

def run_scrape(search_id: int, keywords: str, location: str,
               max_days: Optional[int] = None, experience: str = "mid"):
    """Background task entry point. Scrapes multiple sources."""
    db = SessionLocal()
    try:
        all_jobs = []

        # --- Stage 1: Scrape all sources (0-55%) ---
        _update_search_progress(db, search_id, "scraping", 5, "Searching RemoteOK...")
        remoteok = _scrape_remoteok(keywords)
        all_jobs.extend(remoteok)
        _update_search_progress(db, search_id, "scraping", 12,
                                f"RemoteOK: {len(remoteok)} jobs found")

        _update_search_progress(db, search_id, "scraping", 14, "Searching LinkedIn...")
        linkedin = _scrape_linkedin_guest(keywords, location)
        all_jobs.extend(linkedin)
        _update_search_progress(db, search_id, "scraping", 22,
                                f"LinkedIn: {len(linkedin)} jobs found")

        _update_search_progress(db, search_id, "scraping", 24, "Searching Indeed...")
        indeed = _scrape_indeed(keywords, location)
        all_jobs.extend(indeed)
        _update_search_progress(db, search_id, "scraping", 32,
                                f"Indeed: {len(indeed)} jobs found")

        _update_search_progress(db, search_id, "scraping", 34, "Searching The Muse...")
        muse = _scrape_themuse(keywords, location)
        all_jobs.extend(muse)
        _update_search_progress(db, search_id, "scraping", 40,
                                f"The Muse: {len(muse)} jobs found")

        _update_search_progress(db, search_id, "scraping", 42, "Searching Himalayas...")
        himalayas = _scrape_himalayas(keywords)
        all_jobs.extend(himalayas)
        _update_search_progress(db, search_id, "scraping", 48,
                                f"Himalayas: {len(himalayas)} jobs found")

        _update_search_progress(db, search_id, "scraping", 50, "Searching Jobicy...")
        jobicy = _scrape_jobicy(keywords)
        all_jobs.extend(jobicy)

        total_raw = len(all_jobs)
        _update_search_progress(db, search_id, "scraping", 55,
                                f"Found {total_raw} jobs across 6 sources")

        # Deduplicate by URL
        seen = set()
        jobs = []
        for job in all_jobs:
            url = job.get("url", "")
            if url and url not in seen:
                seen.add(url)
                jobs.append(job)
            elif not url:
                jobs.append(job)

        _update_search_progress(db, search_id, "filtering", 60,
                                f"{len(jobs)} unique jobs (removed {total_raw - len(jobs)} duplicates)")

        # --- Stage 2: Filtering (60-75%) ---
        jobs = _filter_by_experience(jobs, experience)
        _update_search_progress(db, search_id, "filtering", 68,
                                f"{len(jobs)} jobs match experience level")

        jobs = _filter_by_date(jobs, max_days)
        _update_search_progress(db, search_id, "filtering", 75,
                                f"{len(jobs)} jobs after all filters")

        # --- Stage 3: Saving (75-90%) ---
        _update_search_progress(db, search_id, "saving", 78, "Saving new jobs to database...")

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

        _update_search_progress(db, search_id, "saving", 90, f"Saved {inserted} new jobs")

        # --- Stage 4: Scoring (90-100%) ---
        try:
            from .ml import JobRecommender
            recommender = JobRecommender()
            if recommender.model is not None:
                _update_search_progress(db, search_id, "scoring", 93, "Scoring jobs with ML model...")
                recommender.predict_scores(db)
        except Exception:
            pass

        _update_search_progress(db, search_id, "done", 100,
                                f"Done! {inserted} new jobs from {total_raw} found")

        logger.info(f"Inserted {inserted} new jobs for search {search_id} ({total_raw} raw from 6 sources)")
    except Exception as e:
        logger.error(f"Scrape failed for search {search_id}: {e}")
        _update_search_progress(db, search_id, "error", 0, f"Error: {str(e)[:200]}")
    finally:
        db.close()
