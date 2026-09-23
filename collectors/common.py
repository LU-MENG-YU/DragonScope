from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha1
from typing import Any

COLLECTIONS = ("players", "venues", "games", "events", "lineups")

def stable_key(*parts: Any, prefix: str = "e") -> str:
    raw = "|".join("" if p is None else str(p).strip() for p in parts)
    return f"{prefix}-{sha1(raw.encode('utf-8')).hexdigest()[:12]}"

def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

@dataclass
class SourceResult:
    source_id: str
    status: str
    payload: dict[str, list[dict]] = field(default_factory=dict)
    note: str = ""
    error: str | None = None

    @property
    def record_count(self) -> int:
        return sum(len(self.payload.get(k, [])) for k in COLLECTIONS)

    def status_record(self, *, name: str, auth: str, mode: str, previous_success: str | None = None) -> dict:
        checked = now_iso()
        return {
            "id": self.source_id,
            "name": name,
            "status": self.status,
            "auth": auth,
            "mode": mode,
            "last_checked": checked,
            "last_success": checked if self.status in {"ok", "warn"} and self.record_count > 0 else previous_success,
            "records": self.record_count,
            "note": self.note if not self.error else f"{self.note} | {self.error}".strip(" |"),
        }
