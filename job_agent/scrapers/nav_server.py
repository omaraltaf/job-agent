"""
NAV.no MCP Server — exposes job scraping as an MCP tool
"""

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Add parent dir so we can import the scraper
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scrapers.nav_scraper import NavScraper

mcp = FastMCP("NAV.no Job Search")


class MinimalConfig:
    """Minimal config for standalone MCP server use."""
    SEARCH_QUERIES = []
    EXCLUDE_KEYWORDS = []


@mcp.tool()
def search_jobs(queries: list[str]) -> list[dict]:
    """
    Search NAV.no (Arbeidsplassen) for job listings.

    Args:
        queries: List of search terms, e.g. ["UX designer", "product designer"]

    Returns:
        List of job dicts with keys: id, source, title, company, location, url, description
    """
    config = MinimalConfig()
    config.SEARCH_QUERIES = queries
    scraper = NavScraper(config)
    jobs = scraper.fetch_jobs()
    return jobs


if __name__ == "__main__":
    mcp.run(transport="stdio")
