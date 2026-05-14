import re
import httpx
from bs4 import BeautifulSoup

_BASE = "https://boards.greenhouse.io/v1/boards/{slug}/jobs"
_TITLE_RE = re.compile(
    r"\b(software|backend|data|platform|infrastructure|ml|machine\s+learning|site\s+reliability)\s+(engineer|developer)\b",
    re.IGNORECASE,
)


def fetch(config: dict) -> list[dict]:
    jobs: list[dict] = []
    for slug in config["greenhouse"]["companies"]:
        try:
            resp = httpx.get(_BASE.format(slug=slug), params={"content": "true"}, timeout=20)
            resp.raise_for_status()
            for item in resp.json().get("jobs", []):
                if not _TITLE_RE.search(item.get("title", "")):
                    continue
                jobs.append(_normalize(item, slug))
        except Exception as exc:
            print(f"[greenhouse] slug={slug!r} failed: {exc}")
    return jobs


def _normalize(job: dict, company_slug: str) -> dict:
    raw_html = job.get("content") or ""
    description = BeautifulSoup(raw_html, "html.parser").get_text(separator="\n") if raw_html else ""
    location = job.get("location", {})
    loc_name = location.get("name", "") if isinstance(location, dict) else str(location)
    return {
        "id": f"greenhouse_{job['id']}",
        "title": job.get("title", ""),
        "company": company_slug,
        "location": loc_name,
        "remote": "remote" in loc_name.lower(),
        "url": job.get("absolute_url", ""),
        "description": description,
        "posted_at": job.get("updated_at", ""),
        "source": "greenhouse",
    }
