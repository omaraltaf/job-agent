"""
Job Application Agent — Main Orchestrator
Runs once a day, finds new jobs via MCP servers, generates tailored documents
"""

import asyncio
import json
import schedule
import time
import logging
import sys
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Resolve the job_agent directory for path-relative operations
AGENT_DIR = Path(__file__).resolve().parent

from job_agent.modules.job_matcher import JobMatcher
from job_agent.modules.cv_adapter import CVAdapter
from job_agent.modules.cover_letter import CoverLetterGenerator
from job_agent.modules.tracker import ApplicationTracker
from job_agent.modules.notifier import Notifier
from job_agent.config import Config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(AGENT_DIR / "agent.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# MCP server definitions (stdio transport)
PYTHON = sys.executable
SCRAPER_DIR = AGENT_DIR / "scrapers"

MCP_SERVERS = {
    "FINN.no": {
        "config_key": "FINN_ENABLED",
        "server_script": str(SCRAPER_DIR / "finn_server.py"),
    },
    "NAV.no": {
        "config_key": "NAV_ENABLED",
        "server_script": str(SCRAPER_DIR / "nav_server.py"),
    },
}


async def scrape_via_mcp(server_name: str, server_script: str, queries: list[str]) -> list[dict]:
    """Connect to an MCP server and call its search_jobs tool."""
    server_params = StdioServerParameters(
        command=PYTHON,
        args=[server_script],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                "search_jobs",
                arguments={"queries": queries}
            )

            # Parse the result — MCP returns content blocks
            jobs = []
            for content_block in result.content:
                if hasattr(content_block, "text"):
                    try:
                        parsed = json.loads(content_block.text)
                        if isinstance(parsed, list):
                            jobs.extend(parsed)
                        elif isinstance(parsed, dict):
                            jobs.append(parsed)
                    except json.JSONDecodeError:
                        log.warning(f"  Could not parse MCP response from {server_name}")

            log.info(f"  {server_name} (via MCP): {len(jobs)} jobs found")
            return jobs


async def scrape_all_jobs(config: Config) -> list[dict]:
    """Scrape all enabled job boards via MCP servers."""
    all_jobs = []

    for server_name, server_info in MCP_SERVERS.items():
        if not getattr(config, server_info["config_key"], False):
            continue

        try:
            jobs = await scrape_via_mcp(
                server_name,
                server_info["server_script"],
                config.SEARCH_QUERIES,
            )
            all_jobs.extend(jobs)
        except Exception as e:
            log.error(f"  {server_name} MCP failed: {e}")

    return all_jobs


def run_agent():
    log.info("=" * 60)
    log.info(f"Agent starting at {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log.info("=" * 60)

    config = Config()
    tracker = ApplicationTracker(config)
    notifier = Notifier(config)
    matcher = JobMatcher(config)
    cv_adapter = CVAdapter(config)
    cover_letter_gen = CoverLetterGenerator(config)

    stats = {
        "jobs_found": 0,
        "jobs_matched": 0,
        "jobs_applied": 0,
        "jobs_skipped": 0,
        "errors": 0,
        "applied_list": []
    }

    # Step 1: Scrape via MCP servers
    log.info("Scraping job boards via MCP...")
    all_jobs = asyncio.run(scrape_all_jobs(config))
    stats["jobs_found"] = len(all_jobs)

    # Step 2: Filter already applied
    new_jobs = [j for j in all_jobs if not tracker.already_applied(j["id"])]
    log.info(f"New jobs (not yet applied): {len(new_jobs)}")

    # Step 3: Score and filter
    matched_jobs = []
    for job in new_jobs:
        score = matcher.score(job)
        if score >= config.MIN_MATCH_SCORE:
            job["match_score"] = score
            matched_jobs.append(job)

    matched_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    stats["jobs_matched"] = len(matched_jobs)
    stats["jobs_skipped"] = len(new_jobs) - len(matched_jobs)
    log.info(f"Matched jobs (score >= {config.MIN_MATCH_SCORE}): {len(matched_jobs)}")

    # Step 4: Generate documents (CV + cover letter + JD) for each match
    for job in matched_jobs[:config.MAX_APPLICATIONS_PER_RUN]:
        log.info(f"\nPreparing: {job['title']} at {job['company']} (score {job['match_score']}/10)")
        try:
            adapted_cv_path, lang = cv_adapter.adapt(job)
            cover_letter_path = cover_letter_gen.generate(job, adapted_cv_path, lang)
            jd_path = tracker.save_jd(job)

            tracker.record_application(job, adapted_cv_path, cover_letter_path, jd_path)
            stats["jobs_applied"] += 1
            stats["applied_list"].append({
                "title": job["title"],
                "company": job["company"],
                "source": job["source"],
                "score": job["match_score"]
            })
            log.info(f"  Documents saved to {adapted_cv_path.parent}")

        except Exception as e:
            log.error(f"  Error: {e}")
            stats["errors"] += 1

    # Step 5: Notify
    notifier.send_summary(stats)
    log.info(f"\nDone. Prepared documents for {stats['jobs_applied']} jobs.")
    log.info("=" * 60)


def main():
    config = Config()
    run_time = config.SCHEDULE_TIME

    log.info(f"Job Agent started. Runs daily at {run_time}.")
    log.info("Press Ctrl+C to stop.\n")

    run_agent()

    schedule.every().day.at(run_time).do(run_agent)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
