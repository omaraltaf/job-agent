"""
NAV.no Job Scraper (Norwegian government job portal — public API)
"""

import httpx
import logging
from urllib.parse import quote

log = logging.getLogger(__name__)


class NavScraper:
    name = "NAV.no"
    API_URL = "https://arbeidsplassen.nav.no/api/v2/ads"

    def __init__(self, config):
        self.config = config

    def fetch_jobs(self):
        jobs = []
        for query in self.config.SEARCH_QUERIES:
            try:
                results = self._search(query)
                jobs.extend(results)
            except Exception as e:
                log.warning(f"NAV search failed ({query}): {e}")

        # Deduplicate
        seen = set()
        unique = []
        for job in jobs:
            if job["id"] not in seen:
                seen.add(job["id"])
                unique.append(job)
        return unique

    def _search(self, query):
        """
        NAV has a public REST API for job listings
        Docs: https://arbeidsplassen.nav.no/api-doc/
        """
        params = {
            "q": query,
            "size": 25,
            "sort": "published",
        }

        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        # Try the public API endpoint
        try:
            response = httpx.get(
                "https://arbeidsplassen.nav.no/api/v2/ads",
                params=params,
                headers=headers,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_api_response(data)
        except Exception:
            # Fallback: scrape the HTML page
            return self._scrape_html(query)

    def _parse_api_response(self, data):
        jobs = []
        for ad in data.get("content", []):
            job_id = str(ad.get("id", ""))
            jobs.append({
                "id": f"nav_{job_id}",
                "source": "NAV.no",
                "title": ad.get("title", ""),
                "company": ad.get("employer", {}).get("name", "Unknown"),
                "location": ", ".join(
                    [loc.get("municipal", "") for loc in ad.get("locationList", [])]
                ),
                "url": f"https://arbeidsplassen.nav.no/stillinger/stilling/{job_id}",
                "description": ad.get("description", "")[:3000],
            })
        return jobs

    def _scrape_html(self, query):
        """Fallback HTML scraper"""
        from bs4 import BeautifulSoup
        url = f"https://arbeidsplassen.nav.no/stillinger?q={quote(query)}&sort=published"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = httpx.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")

        jobs = []
        for card in soup.select("article, [class*='vacancy-card']"):
            title_el = card.select_one("h2, h3, [class*='title']")
            link_el = card.select_one("a[href]")
            company_el = card.select_one("[class*='employer'], [class*='company']")

            if not title_el or not link_el:
                continue

            href = link_el["href"]
            if not href.startswith("http"):
                href = "https://arbeidsplassen.nav.no" + href

            job_id = href.split("/")[-1]
            jobs.append({
                "id": f"nav_{job_id}",
                "source": "NAV.no",
                "title": title_el.text.strip(),
                "company": company_el.text.strip() if company_el else "Unknown",
                "location": "Norway",
                "url": href,
                "description": "",
            })
        return jobs
