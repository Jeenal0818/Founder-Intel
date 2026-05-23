# Founder's Intel

An automated **competitor intelligence agent** for founders. It researches competitors and market signals on the web, synthesizes a weekly brief, classifies critical vs. routine events, and emails intelligence reports to your team.

## Features

- **ReAct-style research agent** — Plans steps, calls tools (`search_web`, `fetch_page`, `summarize`), and builds a short in-run memory trace
- **Web research** — Tavily search and page extraction
- **LLM synthesis** — OpenRouter (OpenAI-compatible API) for summaries, briefs, and strategic recommendations
- **Alert bucketing** — Rule-based split into critical alerts vs. weekly digest events
- **Email delivery** — Weekly intelligence reports and critical-move alerts via SMTP
- **PostgreSQL logging** — Stores companies and monitoring run history

## Project structure

```
founder_intel_agent/
├── app/
│   ├── agent_core.py          # Research agent, tools, brief generation
│   ├── monitoring_service.py  # Run monitoring + send emails
│   ├── company_service.py     # Register / load companies
│   ├── models.py              # SQLAlchemy models
│   ├── db.py                  # Database engine & sessions
│   ├── config.py              # Environment configuration
│   └── emailer.py             # SMTP helper
└── scripts/
    ├── init_db.py             # Create database tables
    ├── register_company.py    # Example company registration
    └── send_weekly_intel.py   # Trigger a weekly report
```

## Prerequisites

- Python 3.10+
- PostgreSQL
- API keys:
  - [OpenRouter](https://openrouter.ai/) (or compatible OpenAI API key)
  - [Tavily](https://tavily.com/)
- SMTP credentials (e.g. Gmail app password) for sending emails

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/founders-intel.git
cd founders-intel
```

### 2. Create a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `OPENAI_API_KEY` | OpenRouter or OpenAI API key |
| `TAVILY_API_KEY` | Tavily API key |
| `OPENROUTER_BASE_URL` | Default: `https://openrouter.ai/api/v1` |
| `SMTP_HOST` | e.g. `smtp.gmail.com` |
| `SMTP_PORT` | e.g. `587` |
| `SMTP_USER` | Sender email address |
| `SMTP_PASS` | SMTP / app password |

**Never commit `.env` or API keys to Git.** They are listed in `.gitignore`.

### 5. Create the database

Create a PostgreSQL database, then from the **project root**:

```bash
python -c "from founder_intel_agent.app.db import Base, engine; from founder_intel_agent.app import models; Base.metadata.create_all(bind=engine)"
```

Or:

```bash
python founder_intel_agent/scripts/init_db.py
```

### 6. Register a company

Edit `founder_intel_agent/scripts/register_company.py` with your company, competitors, and founder emails, then run:

```bash
python founder_intel_agent/scripts/register_company.py
```

## Usage

### Send a weekly intelligence email

```bash
python founder_intel_agent/scripts/send_weekly_intel.py
```

Update the `company_id` in that script (default: `"notion"`) to match the ID you registered.

### Run monitoring programmatically

```python
from founder_intel_agent.app.monitoring_service import (
    run_company_monitoring,
    send_weekly_intel,
    send_daily_critical_intel,
)

# Research only (no email)
result = run_company_monitoring("notion")

# Weekly email + DB log
send_weekly_intel("notion")

# Critical alerts only (if any critical events found)
send_daily_critical_intel("notion")
```

## How the agent works

1. **Goal** — Built from company competitors and market keywords (last 7 days focus).
2. **Loop** — Up to N steps: LLM chooses `search_web`, `fetch_page`, `summarize`, or `finish`.
3. **Memory** — Short-term string log of thoughts, actions, and truncated observations (per run only; not persisted across runs).
4. **Output** — Founder brief, structured events, critical vs. weekly buckets, and optional strategic recommendations.

## Scheduling (optional)

This repo does not include a built-in scheduler. For production, run scripts on a cron job or cloud scheduler:

| Job | Suggested schedule |
|-----|-------------------|
| Weekly brief | Once per week (e.g. Monday 9:00) |
| Critical alerts | Daily |

Examples: GitHub Actions cron, Render cron, Railway, or system `cron` on a VPS.

## Security

- Store secrets in `.env` locally or in your host’s secret manager in production.
- Rotate any API keys that were ever committed to source control or shared publicly.
- Use a **private** GitHub repository if the codebase should not be public.

## Disclaimer

This tool performs automated web research and sends emails based on LLM output. Always review reports before making business decisions. Search results and summaries may be incomplete or outdated.
