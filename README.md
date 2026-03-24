# Job Application Agent 🤖

Automatically finds jobs on Norwegian job boards, scores them against your profile using AI, and generates tailored CVs and cover letters — ready for you to review and submit.

## What It Does

1. **Scrapes** FINN.no and NAV.no once a day (configurable)
2. **Scores** each job using Claude AI against your professional profile
3. **Detects language** (Norwegian/English) and picks the right CV
4. **Generates** a tailored cover letter per job in the matching language
5. **Saves** CV + cover letter + job description to a local folder
6. **Emails** you a summary of all prepared applications

## Quick Start

### 1. Install
```bash
cd job_agent_package
pip install -e .
```

### 2. Add your CVs
```
job_agent/my_cv/
  master_cv.pdf       ← Norwegian CV
  cv_english.docx     ← English CV
```

### 3. Configure secrets
```bash
cp .env.example .env
```
Edit `.env` with your API keys:
- `ANTHROPIC_API_KEY` — get from [console.anthropic.com](https://console.anthropic.com)
- `GMAIL_APP_PASSWORD` — get from [Google App Passwords](https://myaccount.google.com/apppasswords)

### 4. Configure your profile
```bash
cp job_agent/config.example.py job_agent/config.py
```
Edit `job_agent/config.py` with:
- Your name, email, phone, LinkedIn, portfolio
- Your professional profile (skills, experience, ideal job)
- Your background summary (used for cover letters)
- Job search queries and filters
- Schedule time, notification preferences

### 5. Run
```bash
job-agent
```
Or: `python -m job_agent.agent`

The agent runs immediately on start, then again daily at the configured time (default 08:00).

## Output

Each matched job creates a folder:
```
job_agent/applications/
  2026-03-24_Talentech_Product_Designer/
    CV_Talentech.pdf
    CoverLetter_Talentech.txt
    job_description.txt
    cv_tailoring_notes.txt    (for DOCX CVs)
```

## Configuration

All settings are in `job_agent/config.py`:

| Setting | Description |
|---|---|
| `PROFESSIONAL_PROFILE` | Your skills/experience — used by AI to score jobs |
| `BACKGROUND_SUMMARY` | Your background — used by AI to write cover letters |
| `SEARCH_QUERIES` | Job titles to search for |
| `EXCLUDE_KEYWORDS` | Skip jobs containing these words |
| `MIN_MATCH_SCORE` | Minimum AI score (1-10) to generate documents |
| `MAX_APPLICATIONS_PER_RUN` | Cap per run |
| `AI_MODEL` | Claude model to use |
| `SCHEDULE_TIME` | Daily run time (24h format) |
| `CV_PATH_NO` / `CV_PATH_EN` | Paths to Norwegian/English CVs |
| `NOTIFICATION_METHOD` | `"email"`, `"slack"`, or `"desktop"` |

## Cost

Approximately $2-5/month in Anthropic API credits.

## Project Structure

```
job_agent_package/
├── pyproject.toml              ← Package definition
├── .env                        ← Secrets (not in Git)
├── .env.example                ← Secrets template
├── job_agent/
│   ├── __init__.py
│   ├── agent.py                ← Entry point
│   ├── config.py               ← Your settings (not in Git)
│   ├── config.example.py       ← Settings template
│   ├── scrapers/
│   │   ├── finn_scraper.py
│   │   └── nav_scraper.py
│   ├── modules/
│   │   ├── job_matcher.py      ← AI scoring
│   │   ├── cv_adapter.py       ← Language detection + CV selection
│   │   ├── cover_letter.py     ← Cover letter generation
│   │   ├── applicator.py       ← Browser automation (future use)
│   │   ├── tracker.py          ← SQLite tracking
│   │   └── notifier.py         ← Email notifications
│   ├── my_cv/                  ← Your CVs (not in Git)
│   └── applications/           ← Generated documents (not in Git)
```
