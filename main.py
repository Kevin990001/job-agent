import os
import re
import sys

# Force unbuffered stdout so progress prints appear in real time
sys.stdout.reconfigure(line_buffering=True)
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

import yaml

from deduplicator import Deduplicator
from emailer import send_digest
from scorer import score_jobs
from fetchers import jsearch, greenhouse, lever

_SEEN_PATH = os.path.join(os.path.dirname(__file__), "seen_jobs.json")
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
_TIER_KEYS = ["hot", "recent", "fresh"]


def load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def fetch_all(config: dict) -> list[dict]:
    fetchers = [
        ("jsearch", lambda: jsearch.fetch(config)),
        ("greenhouse", lambda: greenhouse.fetch(config)),
        ("lever", lambda: lever.fetch(config)),
    ]
    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {pool.submit(fn): name for name, fn in fetchers}
        for future in as_completed(futures):
            name = futures[future]
            try:
                jobs = future.result()
                print(f"[{name}] fetched {len(jobs)} jobs")
                results.extend(jobs)
            except Exception as exc:
                print(f"[{name}] fetch error: {exc}")
    return results


def group_by_tier(jobs: list[dict], tier_cfg: dict) -> dict:
    now = datetime.now(tz=timezone.utc)
    tiers: dict[str, list[dict]] = {k: [] for k in _TIER_KEYS}
    tier_hours = [
        ("hot", tier_cfg["hot"]),
        ("recent", tier_cfg["recent"]),
        ("fresh", tier_cfg["fresh"]),
    ]
    for job in sorted(jobs, key=lambda j: j["score"], reverse=True):
        age_h = _age_hours(job.get("posted_at", ""), now)
        for tier, max_h in tier_hours:
            if age_h is None or age_h <= max_h:
                tiers[tier].append(job)
                break
    return {k: v for k, v in tiers.items() if v}


def _age_hours(posted_at: str, now: datetime) -> float | None:
    if not posted_at:
        return None
    try:
        dt = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = now - dt
        return delta.total_seconds() / 3600
    except ValueError:
        return None


_OVERLEVELED = re.compile(
    r"\b(staff\+?|principal|distinguished|fellow|director|vp|vice\s+president|"
    r"head\s+of|engineering\s+manager|senior\s+staff|senior\s+principal|"
    r"president|cto|ceo|cso|svp|evp)\b",
    re.IGNORECASE,
)


def _prefilter(jobs: list[dict]) -> list[dict]:
    kept = [j for j in jobs if not _OVERLEVELED.search(j.get("title", ""))]
    skipped = len(jobs) - len(kept)
    if skipped:
        print(f"  (skipped {skipped} over-leveled titles)")
    return kept


def main() -> None:
    config = load_config()
    dedup = Deduplicator(_SEEN_PATH)

    print("=== Fetching jobs ===")
    all_jobs = fetch_all(config)
    print(f"Total fetched: {len(all_jobs)}")

    new_jobs = dedup.filter_new(all_jobs)
    print(f"New (unseen): {len(new_jobs)}")

    if not new_jobs:
        print("No new jobs — nothing to do.")
        dedup.save()
        return

    new_jobs = _prefilter(new_jobs)
    print(f"After title pre-filter: {len(new_jobs)}")

    print("=== Scoring with Claude ===")
    scored = score_jobs(new_jobs, config)

    # Mark all seen (even low-scorers) before filtering
    dedup.mark_seen(scored)
    dedup.save()
    print(f"seen_jobs.json updated ({len(scored)} new entries)")

    threshold = config["scoring"]["min_score_to_include"]
    qualifying = [j for j in scored if j["score"] >= threshold]
    print(f"Qualifying (score >= {threshold}): {len(qualifying)}")

    if not qualifying:
        print("No qualifying jobs — skipping email.")
        return

    jobs_by_tier = group_by_tier(qualifying, config["scoring"]["tiers"])
    total = sum(len(v) for v in jobs_by_tier.values())
    print(f"Grouped into tiers: { {k: len(v) for k, v in jobs_by_tier.items()} }")

    print("=== Sending email ===")
    send_digest(jobs_by_tier, config)
    print(f"Done — digest sent with {total} jobs.")


if __name__ == "__main__":
    main()
