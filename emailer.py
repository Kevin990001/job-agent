import os
from datetime import datetime
import httpx
from jinja2 import Environment, FileSystemLoader

_RESEND_URL = "https://api.resend.com/emails"
_TIER_ORDER = ["hot", "recent", "fresh"]


def send_digest(jobs_by_tier: dict, config: dict) -> None:
    html = _render(jobs_by_tier, config)
    total = sum(len(v) for v in jobs_by_tier.values())
    subject = f"{config['email']['subject_prefix']} — {datetime.now().strftime('%b %d, %Y')} ({total} jobs)"

    resp = httpx.post(
        _RESEND_URL,
        headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
        json={
            "from": config["email"]["from"],
            "to": [config["email"]["to"]],
            "subject": subject,
            "html": html,
        },
        timeout=20,
    )
    resp.raise_for_status()
    print(f"[emailer] sent digest: {subject}")


def _render(jobs_by_tier: dict, config: dict) -> str:
    templates_dir = os.path.join(os.path.dirname(__file__), "templates")
    env = Environment(loader=FileSystemLoader(templates_dir), autoescape=True)
    tmpl = env.get_template("digest.html")

    max_per_tier = config["email"].get("max_jobs_per_tier", 5)
    capped = {tier: jobs_by_tier.get(tier, [])[:max_per_tier] for tier in _TIER_ORDER}
    total = sum(len(v) for v in capped.values())

    return tmpl.render(
        date=datetime.now().strftime("%B %d, %Y"),
        total=total,
        tiers=capped,
    )
