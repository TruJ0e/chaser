from __future__ import annotations

import json
import threading
from pathlib import Path

from .models import ActivityEvent


class ActivityLog:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()

    def append(self, event: ActivityEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = event.model_dump_json() + "\n"
        with self._lock, self.path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()

    def read(self, limit: int = 100) -> list[dict]:
        if not self.path.exists():
            return []
        with self._lock, self.path.open("r", encoding="utf-8") as handle:
            rows = [json.loads(line) for line in handle if line.strip()]
        return list(reversed(rows[-limit:]))
