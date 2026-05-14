import re
from datetime import datetime, timezone
import httpx

_BASE = "https://api.lever.co/v0/postings/{slug}"
_TITLE_RE = re.compile(
    r"\b(software|backend|data|platform|infrastructure|ml|machine\s+learning|site\s+reliability)\s+(engineer|developer)\b",
    re.IGNORECASE,
)


def fetch(config: dict) -> list[dict]:
    jobs: list[dict] = []
    for slug in config["lever"]["companies"]:
        try:
            resp = httpx.get(
                _BASE.format(slug=slug),
                params={"mode": "json", "limit": "50"},
                timeout=20,
            )
            resp.raise_for_status()
            for item in resp.json():
                if not _TITLE_RE.search(item.get("text", "")):
                    continue
                jobs.append(_normalize(item, slug))
        except Exception as exc:
            print(f"[lever] slug={slug!r} failed: {exc}")
    return jobs


def _normalize(posting: dict, company_slug: str) -> dict:
    created_ms = posting.get("createdAt", 0) or 0
    posted_at = datetime.fromtimestamp(created_ms / 1000, tz=timezone.utc).isoformat()
    categories = posting.get("categories", {}) or {}
    location = categories.get("location", "")
    workplace = posting.get("workplaceType", "")
    description = "\n".join(
        filter(None, [posting.get("descriptionPlain", ""), posting.get("additionalPlain", "")])
    )
    return {
        "id": f"lever_{posting['id']}",
        "title": posting.get("text", ""),
        "company": company_slug,
        "location": location,
        "remote": workplace == "remote",
        "url": posting.get("hostedUrl", ""),
        "description": description,
        "posted_at": posted_at,
        "source": "lever",
    }
