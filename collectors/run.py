#!/usr/bin/env python3
"""Collector orchestrator for GitHub Actions.

Core behavior:
- prefer the canonical JSON dataset for Python reads;
- keep the JS bundle only as a browser-friendly mirror/fallback;
- reject unresolved Git merge-conflict markers early with a clear error;
- dynamically load enabled source adapters;
- upsert normalized records by stable id;
- preserve last known good public data if a source fails;
- update source health independently;
- write both JSON and JS bundles from the same normalized object.
"""
from __future__ import annotations

import argparse
import importlib
import inspect
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JS = ROOT / "data" / "public-data.js"
JSON = ROOT / "data" / "public-data.json"
CONF = ROOT / "config" / "sources.json"

MODULES = {
    "cpbl_stats": "collectors.sources.cpbl_stats",
    "cpbl": "collectors.sources.cpbl",
    "news": "collectors.sources.rss",
    "wdragons": "collectors.sources.rss",
    "venues": "collectors.sources.venues",
    "weather": "collectors.sources.weather",
}
COLLECTIONS = ("players", "venues", "games", "events", "lineups")
CONFLICT_TOKENS = ("<<<<<<< ", "\n=======", ">>>>>>> ")


def _reject_conflict_markers(text: str, path: Path) -> None:
    if any(token in text for token in CONFLICT_TOKENS):
        raise RuntimeError(
            f"{path.relative_to(ROOT)} contains unresolved Git merge-conflict markers"
        )


def _load_json_file(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    _reject_conflict_markers(text, path)
    return json.loads(text)


def _load_js_bundle(path: Path) -> dict:
    text = path.read_text(encoding="utf-8-sig")
    _reject_conflict_markers(text, path)
    match = re.search(
        r"window\.WD_INTEL_DATA\s*=\s*(\{.*\})\s*;\s*$",
        text,
        re.S,
    )
    if not match:
        raise RuntimeError(f"Cannot parse {path.relative_to(ROOT)}")
    return json.loads(match.group(1))


def load_data() -> dict:
    """Load the canonical public dataset.

    Python collectors read public-data.json first. public-data.js exists primarily
    for the static frontend and is only a fallback for older checkouts.
    """
    errors: list[str] = []

    if JSON.exists():
        try:
            return _load_json_file(JSON)
        except Exception as exc:
            errors.append(f"{JSON.name}: {exc}")

    if JS.exists():
        try:
            return _load_js_bundle(JS)
        except Exception as exc:
            errors.append(f"{JS.name}: {exc}")

    detail = " | ".join(errors) if errors else "dataset files are missing"
    raise RuntimeError(f"Cannot load public dataset. {detail}")


def write_bundle(data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    JSON.write_text(payload + "\n", encoding="utf-8")
    JS.write_text("window.WD_INTEL_DATA = " + payload + ";\n", encoding="utf-8")


def upsert(existing: list[dict], incoming: list[dict]) -> list[dict]:
    keyed = {x["id"]: x for x in existing if x.get("id")}
    keyless = [x for x in existing if not x.get("id")]
    for item in incoming:
        if item.get("id"):
            old = keyed.get(item["id"], {})
            keyed[item["id"]] = {
                **old,
                **{k: v for k, v in item.items() if v not in (None, "")},
            }
        else:
            keyless.append(item)
    return list(keyed.values()) + keyless


def status_map(data: dict) -> dict:
    return {
        item.get("id"): item
        for item in data.get("source_status", [])
        if item.get("id")
    }


def run_source(source_id, cfg, previous_status, data):
    module_name = MODULES.get(source_id)
    if not module_name:
        raise RuntimeError(f"No module registered for source {source_id}")

    module = importlib.import_module(module_name)
    params = inspect.signature(module.collect).parameters
    result = module.collect(cfg, data=data) if "data" in params else module.collect(cfg)

    name = cfg.get("name", source_id.upper())
    auth = cfg.get("auth", "none")
    mode = cfg.get("mode", Path(cfg.get("adapter", "")).stem or "adapter")
    status = result.status_record(
        name=name,
        auth=auth,
        mode=mode,
        previous_success=(previous_status or {}).get("last_success"),
    )
    return result, status


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--touch", action="store_true")
    args = parser.parse_args()

    data = load_data()
    config = json.loads(CONF.read_text(encoding="utf-8"))
    statuses = status_map(data)

    if args.touch:
        data.setdefault("meta", {})["generated_at"] = (
            datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
        )
        write_bundle(data)
        print("Touched bundle.")
        return

    enabled = {
        key: value
        for key, value in config.get("sources", {}).items()
        if value.get("enabled")
    }
    if not enabled:
        print("No live collectors enabled. Existing dataset preserved.")
        return

    changed = False
    for source_id, cfg in enabled.items():
        try:
            result, status = run_source(
                source_id, cfg, statuses.get(source_id), data
            )
            statuses[source_id] = status

            if result.status in {"ok", "warn"}:
                for collection in COLLECTIONS:
                    incoming = result.payload.get(collection, [])
                    if incoming:
                        data[collection] = upsert(
                            data.get(collection, []), incoming
                        )
                        changed = True

            print(
                f"{source_id}: {result.status} "
                f"({result.record_count} records)"
            )
        except Exception as exc:
            previous = statuses.get(
                source_id,
                {
                    "id": source_id,
                    "name": source_id.upper(),
                    "auth": cfg.get("auth", "none"),
                    "mode": "adapter",
                    "records": 0,
                },
            )
            previous = {
                **previous,
                "status": "bad",
                "last_checked": datetime.now()
                .astimezone()
                .isoformat(timespec="seconds"),
                "note": (
                    "Collector exception; previous dataset preserved. "
                    f"{exc}"
                ),
            }
            statuses[source_id] = previous
            print(f"{source_id}: bad ({exc})")

    data["source_status"] = list(statuses.values())
    meta = data.setdefault("meta", {})
    if changed:
        meta["mode"] = "PUBLIC_CACHE"
    meta["generated_at"] = datetime.now().astimezone().strftime(
        "%Y-%m-%d %H:%M %z"
    )

    write_bundle(data)
    print(
        "Bundle written."
        if changed
        else "Health updated; existing records preserved."
    )


if __name__ == "__main__":
    main()
