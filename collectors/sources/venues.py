from __future__ import annotations

import json
from pathlib import Path
from collectors.common import SourceResult, stable_key

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "config" / "venues.json"

def collect(config: dict) -> SourceResult:
    raw = json.loads(REGISTRY.read_text(encoding="utf-8"))
    venues = []
    for v in raw.get("venues", []):
        source_name = str(v.get("source_name") or v.get("name") or "").strip()
        if not source_name:
            continue
        out = {
            "id": stable_key(source_name, prefix="v"),
            "name": v.get("name") or source_name,
            "source_name": source_name,
            "city": v.get("city") or "",
            "indoor": bool(v.get("indoor")),
            "source": "DragonScope venue registry",
        }
        if v.get("latitude") is not None and v.get("longitude") is not None:
            out["latitude"] = float(v["latitude"])
            out["longitude"] = float(v["longitude"])
        venues.append(out)
    return SourceResult("venues","ok" if venues else "warn",{"venues":venues},note=f"{len(venues)} 個球場")
