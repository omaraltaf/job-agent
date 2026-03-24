"""
FINN.no Job Scraper
"""

import httpx
import logging
from bs4 import BeautifulSoup
from urllib.parse import quote

log = logging.getLogger(__name__)


class FinnScraper:
    name = "FINN.no"
    BASE_URL = "https://www.finn.no/job/search"

    def __init__(self, config):
        self.config = config

    def fetch_jobs(self):
        jobs = []
        for query in self.config.SEARCH_QUERIES:
            try:
                results = self._search(query)
                jobs.extend(results)
            except Exception as e:
                log.warning(f"FINN search failed ({query}): {e}")

        seen = set()
        unique = []
        for job in jobs:
            if job["id"] not in seen:
                seen.add(job["id"])
                unique.append(job)
        return unique

    def _search(self, query):
        url = f"{self.BASE_URL}?q={quote(query)}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

        response = httpx.get(url, headers=headers, timeout=15, follow_redirects=True)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        jobs = []

        for card in soup.select("article"):
            try:
                title_el = card.select_one("a.job-card-link")
                company_el = card.select_one(".text-caption strong")

                href = title_el.get("href", "") if title_el else ""
                if not href:
                    continue
                if not href.startswith("http"):
                    href = "https://www.finn.no" + href

                finn_id = href.split("/")[-1].split("?")[0]
                location_el = card.select_one(".text-caption span")

                jobs.append({
                    "id": f"finn_{finn_id}",
                    "source": "FINN.no",
                    "title": title_el.text.strip() if title_el else "Unknown",
                    "company": company_el.text.strip() if company_el else "Unknown",
                    "location": location_el.text.strip() if location_el else "Norway",
                    "url": href,
                    "description": self._fetch_description(href),
                })
            except Exception as e:
                log.debug(f"Error parsing FINN card: {e}")
                continue

        return jobs

    def _fetch_description(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            r = httpx.get(url, headers=headers, timeout=10, follow_redirects=True)
            soup = BeautifulSoup(r.text, "html.parser")
            desc = soup.select_one("[class*='description'], [class*='job-text'], article")
            return desc.get_text(separator="\n").strip()[:3000] if desc else ""
        except Exception:
            return ""
