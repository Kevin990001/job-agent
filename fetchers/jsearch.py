import os
import httpx

_HOST = "jsearch.p.rapidapi.com"
_URL = f"https://{_HOST}/search"
_HEADERS = lambda: {
    "X-RapidAPI-Key": os.environ["JSEARCH_API_KEY"],
    "X-RapidAPI-Host": _HOST,
}


def fetch(config: dict) -> list[dict]:
    cfg = config["jsearch"]
    jobs: list[dict] = []
    for query in cfg["queries"]:
        params = {
            "query": query,
            "location": cfg["location"],
            "employment_types": cfg["employment_types"],
            "date_posted": cfg["date_posted"],
            "page": "1",
            "num_pages": str(cfg["num_pages"]),
        }
        try:
            resp = httpx.get(_URL, headers=_HEADERS(), params=params, timeout=30)
            resp.raise_for_status()
            for item in resp.json().get("data", []):
                jobs.append(_normalize(item))
        except Exception as exc:
            print(f"[jsearch] query={query!r} failed: {exc}")
    return jobs


def _normalize(job: dict) -> dict:
    return {
        "id": f"jsearch_{job.get('job_id', '')}",
        "title": job.get("job_title", ""),
        "company": job.get("employer_name", ""),
        "location": _location(job),
        "remote": bool(job.get("job_is_remote")),
        "url": job.get("job_apply_link") or job.get("job_google_link", ""),
        "description": job.get("job_description", ""),
        "posted_at": job.get("job_posted_at_datetime_utc", ""),
        "source": "linkedin",
    }


def _location(job: dict) -> str:
    parts = [job.get("job_city", ""), job.get("job_state", ""), job.get("job_country", "")]
    return ", ".join(p for p in parts if p)
