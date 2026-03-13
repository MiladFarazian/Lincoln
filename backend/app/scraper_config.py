"""LinkedIn scraper configuration — CSS selectors and constants.
Update selectors here when LinkedIn changes its DOM structure."""

# CSS selectors for LinkedIn public job search pages
SELECTORS = {
    "job_list": ".jobs-search__results-list",
    "job_card": ".jobs-search__results-list li",
    "title": ".base-search-card__title",
    "company": ".base-search-card__subtitle",
    "location": ".job-search-card__location",
    "link": "a.base-card__full-link",
    "date": "time",
    "date_attr": "datetime",
    "description": ".show-more-less-html__markup",
    "salary": ".job-search-card__salary-info",
}

# User-agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]

# Viewport options
VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1280, "height": 720},
]

# Rate limiting
DELAY_MIN = 2.0
DELAY_MAX = 5.0
DETAIL_DELAY_MIN = 1.0
DETAIL_DELAY_MAX = 3.0
MAX_PAGES = 3
JOBS_PER_PAGE = 25
