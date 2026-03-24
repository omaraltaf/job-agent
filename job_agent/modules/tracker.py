"""
Application Tracker — SQLite database + local file storage
"""

import sqlite3
import json
import logging
import shutil
from pathlib import Path
from datetime import datetime

log = logging.getLogger(__name__)


class ApplicationTracker:
    def __init__(self, config=None):
        self.db_path = config.DB_PATH if config else Path("tracker.db")
        self.output_dir = config.OUTPUT_DIR if config else Path("applications")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    title TEXT,
                    company TEXT,
                    source TEXT,
                    location TEXT,
                    url TEXT,
                    match_score INTEGER,
                    applied_at TEXT,
                    cv_path TEXT,
                    cover_letter_path TEXT,
                    jd_path TEXT,
                    folder_path TEXT,
                    status TEXT DEFAULT 'applied'
                )
            """)
            conn.commit()

    def already_applied(self, job_id: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM applications WHERE job_id = ?", (job_id,)
            ).fetchone()
            return row is not None

    def record_application(self, job: dict, cv_path: Path, cover_letter_path: Path, jd_path: Path):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR IGNORE INTO applications 
                (job_id, title, company, source, location, url, match_score, 
                 applied_at, cv_path, cover_letter_path, jd_path, folder_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                job["id"],
                job["title"],
                job["company"],
                job["source"],
                job.get("location", ""),
                job["url"],
                job.get("match_score", 0),
                datetime.now().isoformat(),
                str(cv_path) if cv_path else "",
                str(cover_letter_path) if cover_letter_path else "",
                str(jd_path) if jd_path else "",
                str(cv_path.parent) if cv_path else "",
            ))
            conn.commit()
        log.debug(f"Recorded application: {job['title']} at {job['company']}")

    def save_jd(self, job: dict) -> Path:
        """Save job description to the application folder"""
        folder = self._get_job_folder(job)
        folder.mkdir(parents=True, exist_ok=True)

        jd_path = folder / "job_description.txt"
        content = f"""JOB: {job['title']}
COMPANY: {job['company']}
SOURCE: {job['source']}
LOCATION: {job.get('location', '')}
URL: {job['url']}
MATCH SCORE: {job.get('match_score', 'N/A')}/10
SAVED: {datetime.now().strftime('%Y-%m-%d %H:%M')}

{'=' * 60}

{job.get('description', 'No description available')}
"""
        jd_path.write_text(content, encoding="utf-8")
        return jd_path

    def get_all_applications(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM applications ORDER BY applied_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]

    def get_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
            today = conn.execute(
                "SELECT COUNT(*) FROM applications WHERE date(applied_at) = date('now')"
            ).fetchone()[0]
            by_source = conn.execute(
                "SELECT source, COUNT(*) as count FROM applications GROUP BY source"
            ).fetchall()
        return {"total": total, "today": today, "by_source": dict(by_source)}

    def _get_job_folder(self, job: dict) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        safe_company = "".join(c for c in job["company"] if c.isalnum() or c in " _-")[:30]
        safe_title = "".join(c for c in job["title"] if c.isalnum() or c in " _-")[:30]
        folder_name = f"{date_str}_{safe_company}_{safe_title}".replace(" ", "_")
        return self.output_dir / folder_name
