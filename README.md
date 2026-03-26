# Job Application Agent 🤖

Automatically finds jobs on Norwegian job boards, scores them against your profile using AI, and generates tailored CVs and cover letters — ready for you to review and submit.

## What It Does

1. **Scrapes** FINN.no and NAV.no once a day (configurable)
2. **Scores** each job using Claude AI against your professional profile
3. **Smart Job Caching**: Remembers previously evaluated jobs across runs to heavily save on API credits
4. **Detects language** (Norwegian/English) and picks the right CV context
5. **Generates** a tailored cover letter and perfectly formatted Word document (`.docx`) CV per job
6. **Saves** documents beautifully formatted with native Microsoft Word styling
7. **Emails** you a summary of all prepared applications

## Quick Start
You can run this project locally to fully automate your job application pipeline on autopilot.

### 1. Install via Git
```bash
git clone https://github.com/omaraltaf/job-agent.git
cd job-agent

# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install the agent alongside its dependencies
pip install -e .
```

### 2. Add your CVs
Place your master CVs in the folder structure below. The agent supports parsing PDF or DOCX:
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
# Set up your generic profile configuration
cp job_agent/config.example.py job_agent/config.py
```
Edit `job_agent/config.py` with:
- Your name, email, phone, LinkedIn, portfolio
- Your general professional profile (skills, experience, ideal job)
- Your background summary (used by Claude for cover letters)
- Search queries and exclude filtering

### 5. Run the Agent
```bash
job-agent
```
Or run the python module directly:
```bash
python -m job_agent.agent
```

The agent runs immediately on start, pulling new jobs, and then repeats its execution cycle daily at the configured time (default 08:00).

## Output

Each matched job generates a polished, submission-ready set of Microsoft Word documents inside an easily identifiable target folder:
```
job_agent/applications/
  2026-03-26_Talentech_Senior_Developer/
    CV_Talentech.docx
    CoverLetter_Talentech.docx
    job_description.txt
```

## Cost

Due to the internal Database caching and precision MCP pipelines, the agent operates incredibly cheaply, only using approximately $2-5/month in Anthropic API credits when processing hundreds of highly relevant roles.
