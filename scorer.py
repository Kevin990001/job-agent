import json
import anthropic

_CLIENT = None

_SYSTEM_PREFIX = """\
You are a technical recruiter evaluating job fit for a software engineer candidate.
Score how well the candidate matches the job posting on a scale of 1-10:
  10 — Perfect: all required skills present, ideal seniority, role type match
  7-9 — Strong: most skills present, minor gaps easily bridged
  5-6 — Decent: core skills align but some notable gaps
  3-4 — Weak: significant skill or experience gaps
  1-2 — Poor: fundamentally misaligned role or experience level

Respond ONLY with valid JSON, exactly this structure (no extra keys, no markdown):
{"score": <integer 1-10>, "rationale": "<one sentence>", "missing": ["<skill>", ...]}\
"""


def _client() -> anthropic.Anthropic:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = anthropic.Anthropic()
    return _CLIENT


def _candidate_block(config: dict) -> str:
    c = config["candidate"]
    return (
        f"CANDIDATE PROFILE:\n"
        f"Name: {c['name']}\n"
        f"Current role: {c['current_role']}\n"
        f"Years of experience: {c['years_experience']}\n"
        f"Skills: {', '.join(c['skills'])}\n\n"
        f"Summary:\n{c['resume_summary'].strip()}"
    )


def score_jobs(jobs: list[dict], config: dict) -> list[dict]:
    candidate_block = _candidate_block(config)
    system_content = _SYSTEM_PREFIX + "\n\n" + candidate_block

    scored = []
    total = len(jobs)
    for i, job in enumerate(jobs, 1):
        result = _score_one(job, system_content)
        scored.append({**job, **result})
        print(f"  [{i}/{total}] {job['title']} @ {job['company']} → {result['score']}/10", flush=True)
    return scored


def _score_one(job: dict, system_content: str) -> dict:
    user_msg = (
        f"JOB POSTING:\n"
        f"Title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}"
        + (" (Remote)" if job.get("remote") else "")
        + f"\n\nDescription:\n{job['description'][:3000]}"
    )

    for attempt in range(2):
        try:
            resp = _client().messages.create(
                model="claude-sonnet-4-6",
                max_tokens=256,
                system=[
                    {
                        "type": "text",
                        "text": system_content,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[{"role": "user", "content": user_msg}],
            )
            raw = resp.content[0].text.strip()
            # Strip accidental markdown fences
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = json.loads(raw)
            return {
                "score": int(data["score"]),
                "rationale": str(data.get("rationale", "")),
                "missing": list(data.get("missing", [])),
            }
        except Exception as exc:
            if attempt == 0:
                print(f"[scorer] retry for {job['id']}: {exc}")
            else:
                print(f"[scorer] failed for {job['id']}: {exc}")
    return {"score": 0, "rationale": "scoring failed", "missing": []}
