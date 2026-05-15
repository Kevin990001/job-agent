# Job Agent

An automated job discovery and digest tool that fetches new postings from multiple sources, scores them against a candidate profile using Claude AI, and sends a daily email digest.

## How It Works

1. **Fetch** — pulls job listings in parallel from:
   - **JSearch** (LinkedIn jobs via RapidAPI)
   - **Greenhouse** (direct public API, no auth required)
   - **Lever** (direct public API, no auth required)
2. **Deduplicate** — skips jobs already seen in previous runs (tracked in `seen_jobs.json`)
3. **Pre-filter** — drops over-leveled titles (Staff+, Principal, Director, VP, etc.)
4. **Score** — sends each job to `claude-sonnet-4-6` with the candidate profile; returns a 1–10 fit score, one-sentence rationale, and missing skills
5. **Tier** — groups qualifying jobs into Hot (≤24h), Recent (≤48h), and Fresh (≤7d) buckets
6. **Email** — renders an HTML digest via Jinja2 and sends it through [Resend](https://resend.com)

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
export ANTHROPIC_API_KEY=your_anthropic_key
export JSEARCH_API_KEY=your_rapidapi_key   # for JSearch/LinkedIn results
export RESEND_API_KEY=your_resend_key      # for email delivery
```

### 3. Configure your profile

Edit `config.yaml` to set your candidate profile, target companies, scoring thresholds, and email settings.

### 4. Run

```bash
python main.py
```

## Configuration (`config.yaml`)

| Section | Key | Description |
|---|---|---|
| `candidate` | `name`, `skills`, `resume_summary`, … | Your profile used for AI scoring |
| `scoring` | `min_score_to_include` | Minimum score (1–10) to include a job in the digest |
| `scoring` | `tiers.hot/recent/fresh` | Age thresholds (hours) for email tier grouping |
| `jsearch` | `queries`, `location`, `num_pages` | LinkedIn search parameters |
| `greenhouse` | `companies` | List of Greenhouse company slugs to scrape |
| `lever` | `companies` | List of Lever company slugs to scrape |
| `email` | `from`, `to`, `subject_prefix` | Email delivery settings |

## Project Structure

```
job-agent/
├── main.py              # Orchestrator: fetch → filter → score → email
├── scorer.py            # Claude AI scoring with prompt caching
├── deduplicator.py      # Tracks seen job IDs across runs
├── emailer.py           # Sends HTML digest via Resend API
├── config.yaml          # Candidate profile and all settings
├── fetchers/
│   ├── jsearch.py       # LinkedIn jobs via JSearch/RapidAPI
│   ├── greenhouse.py    # Greenhouse public job board API
│   └── lever.py         # Lever public job board API
└── templates/
    └── digest.html      # Jinja2 email template
```

## Automate with Cron

To run daily at 8 AM:

```cron
0 8 * * * cd /path/to/job-agent && python main.py >> logs/job-agent.log 2>&1
```
