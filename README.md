# JobApply Agent 🤖

An intelligent autonomous agent that streamlines your job application process — from discovering relevant listings to crafting personalized cover letters and tracking application status.

---

## Overview

JobApply Agent automates the end-to-end job hunt workflow so you can focus on preparing for interviews rather than spending hours filling out forms and writing tailored applications.

The agent:
- Searches job boards based on your skills, role preferences, and location
- Scores and filters listings against your resume and preferences
- Generates personalized cover letters and application materials
- Submits applications automatically where supported
- Tracks every application and its current status in a clean dashboard

---

## Features

| Feature | Description |
|---|---|
| **Smart Job Discovery** | Scrapes and aggregates listings from LinkedIn, Indeed, Greenhouse, Lever, and more |
| **Resume Matching** | Scores each job against your resume using semantic similarity |
| **Cover Letter Generation** | Produces tailored, human-sounding cover letters per job |
| **Auto Apply** | Fills and submits applications on supported platforms |
| **Application Tracker** | Persists all applications with status, company, role, and date |
| **Email Notifications** | Sends daily digest of new matches and status updates |
| **CLI + Web UI** | Use via terminal or a lightweight dashboard |

---

## Architecture

```
jobapplyAgent/
├── agent/
│   ├── scraper.py          # Job board scrapers
│   ├── matcher.py          # Resume ↔ job matching logic
│   ├── cover_letter.py     # Cover letter generation
│   ├── applier.py          # Form filling & submission
│   └── tracker.py          # Application state management
├── config/
│   ├── preferences.yaml    # User job preferences
│   └── platforms.yaml      # Supported job board configs
├── ui/
│   └── dashboard.py        # Web dashboard (Streamlit)
├── data/
│   └── applications.db     # SQLite store for tracked applications
├── tests/
├── .env.example
├── requirements.txt
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) or `pip`
- A resume in PDF or DOCX format
- API keys (see Configuration)

### Installation

```bash
git clone https://github.com/Mohakgarg5/jobapplyAgent.git
cd jobapplyAgent

# Install dependencies
pip install -r requirements.txt

# Copy and fill in your config
cp .env.example .env
```

### Configuration

Edit `.env`:

```env
# LLM
ANTHROPIC_API_KEY=your_key_here

# Job board credentials (optional for auto-apply)
LINKEDIN_EMAIL=you@example.com
LINKEDIN_PASSWORD=your_password

# Notification (optional)
SMTP_HOST=smtp.gmail.com
SMTP_USER=you@example.com
SMTP_PASS=your_app_password
NOTIFY_EMAIL=you@example.com
```

Edit `config/preferences.yaml`:

```yaml
roles:
  - Software Engineer
  - Backend Engineer
  - ML Engineer

locations:
  - Remote
  - San Francisco, CA
  - New York, NY

experience_years: 3
salary_min: 120000

resume_path: ./resume.pdf

keywords_required:
  - Python
  - distributed systems

keywords_excluded:
  - unpaid
  - internship
```

### Run the Agent

```bash
# One-time run — find, score, and apply
python -m agent.run

# Launch the dashboard
streamlit run ui/dashboard.py

# Schedule via cron (daily at 8 AM)
0 8 * * * cd /path/to/jobapplyAgent && python -m agent.run
```

---

## How It Works

```
┌─────────────────┐
│  Preferences &  │
│     Resume      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  Job Scraper    │────▶│  Listings Database   │
│  (multi-board)  │     └──────────┬───────────┘
└─────────────────┘                │
                                   ▼
                        ┌──────────────────────┐
                        │   Resume Matcher     │
                        │  (score & filter)    │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  Cover Letter Agent  │
                        │  (per-job tailored)  │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Auto Applier       │
                        │  (form fill + submit)│
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  Application Tracker │
                        │  + Notifications     │
                        └──────────────────────┘
```

---

## Roadmap

- [ ] LinkedIn Easy Apply support
- [ ] Indeed Quick Apply support
- [ ] ATS-optimized resume tailoring per job
- [ ] Interview scheduler integration
- [ ] Slack notification support
- [ ] Docker image for self-hosting
- [ ] Multi-resume profile support

---

## Contributing

Contributions are welcome! Please open an issue to discuss your idea before submitting a PR.

```bash
# Fork the repo, then:
git checkout -b feature/your-feature
git commit -m "feat: add your feature"
git push origin feature/your-feature
# Open a Pull Request
```

---

## License

[MIT](LICENSE)

---

## Disclaimer

Use this tool responsibly and in accordance with each platform's Terms of Service. Automated scraping and applying may be restricted on some job boards.
