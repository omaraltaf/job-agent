"""
Configuration Template — copy this file to job_agent/config.py and fill in your details.
Secrets (API keys) go in .env — see .env.example

DO NOT commit config.py or .env to Git
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # ─── Your Profile ───────────────────────────────────────────
    YOUR_NAME = "Your Full Name"
    YOUR_EMAIL = "your@email.com"
    YOUR_PHONE = "+47 000 00 000"
    YOUR_LOCATION = "Oslo, Norway"
    YOUR_LINKEDIN = "https://linkedin.com/in/yourprofile"
    YOUR_PORTFOLIO = "https://yourportfolio.com"

    # ─── Your CV ────────────────────────────────────────────────
    CV_PATH_NO = BASE_DIR / "my_cv/master_cv.pdf"     # Norwegian CV
    CV_PATH_EN = BASE_DIR / "my_cv/cv_english.docx"   # English CV
    CV_DEFAULT_LANG = "no"                             # Fallback: "no" or "en"

    # ─── Professional Profile (used by job matcher) ─────────────
    # Claude uses this to score how well each job matches you.
    PROFESSIONAL_PROFILE = """
ROLE: Your Role Title

SKILLS:
- Skill 1
- Skill 2
- Skill 3

EXPERIENCE LEVEL: Junior / Mid / Senior
PREFERRED: Remote-first or hybrid, your area

IDEAL JOB:
- Type of role you're looking for
- Type of company/product

NOT INTERESTED IN:
- Roles you don't want
"""

    # ─── Background Summary (used by cover letter generator) ────
    # Claude uses this to write personalised cover letters.
    BACKGROUND_SUMMARY = """
Describe your professional background in 3-5 sentences.
Include your key strengths, experience areas, and what you bring to a team.
"""

    # ─── Job Search ─────────────────────────────────────────────
    SEARCH_QUERIES = [
        "your job title",
        "alternative title",
    ]

    SEARCH_LOCATIONS = []  # Not used — searches nationally

    # ─── Filtering ───────────────────────────────────────────────
    MIN_MATCH_SCORE = 6
    MAX_APPLICATIONS_PER_RUN = 10
    EXCLUDE_KEYWORDS = [
        "irrelevant role 1",
        "irrelevant role 2",
    ]

    # ─── AI Model ────────────────────────────────────────────────
    AI_MODEL = "claude-sonnet-4-20250514"

    # ─── Storage ─────────────────────────────────────────────────
    OUTPUT_DIR = BASE_DIR / "applications"
    DB_PATH = BASE_DIR / "tracker.db"

    # ─── Notifications ───────────────────────────────────────────
    NOTIFICATION_METHOD = "email"   # "email", "slack", or "desktop"
    NOTIFY_EMAIL = "your@email.com"

    # ─── Schedule ────────────────────────────────────────────────
    SCHEDULE_TIME = "08:00"         # Daily run time (24h format)

    # ─── Job Boards ──────────────────────────────────────────────
    FINN_ENABLED = True
    NAV_ENABLED = False
    INDEED_ENABLED = False

    # ─── Application Behaviour (for applicator.py) ───────────────
    DELAY_BETWEEN_APPLICATIONS = 30
    HEADLESS_BROWSER = False
    AUTO_SUBMIT = False

    # ─── API Keys (loaded from .env) ─────────────────────────────
    # Set these in your .env file, not here
    import os
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
