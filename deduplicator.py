import json
import os
from datetime import datetime, timedelta, timezone


class Deduplicator:
    def __init__(self, path: str):
        self._path = path
        self._data: dict[str, str] = {}
        if os.path.exists(path):
            with open(path) as f:
                self._data = json.load(f).get("seen", {})

    def filter_new(self, jobs: list[dict]) -> list[dict]:
        return [j for j in jobs if j["id"] not in self._data]

    def mark_seen(self, jobs: list[dict]) -> None:
        now = datetime.now(tz=timezone.utc).isoformat()
        for job in jobs:
            self._data.setdefault(job["id"], now)

    def prune(self, days: int = 30) -> None:
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        self._data = {
            k: v
            for k, v in self._data.items()
            if _parse_dt(v) > cutoff
        }

    def save(self) -> None:
        self.prune()
        with open(self._path, "w") as f:
            json.dump({"seen": self._data}, f, indent=2)


def _parse_dt(iso: str) -> datetime:
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
