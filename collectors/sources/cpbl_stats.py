"""Public CPBL Stats roster collector.

The stats site is a public Next.js application.  The player-list page embeds its
roster payload in the streamed page data.  We extract only public identity and
position metadata; performance analysis remains outside this intelligence app.
"""
from __future__ import annotations

import json
import re
from typing import Any

import requests

from collectors.common import SourceResult

BASE = "https://stats.cpbl.com.tw"
DRAGONS_PREFIX = "AAA"
POSITION = {
    "1": "投手", "2": "捕手",
    "3": "內野手", "4": "內野手", "5": "內野手", "6": "內野手",
    "7": "外野手", "8": "外野手", "9": "外野手",
    "10": "指定打擊", "11": "代打",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    })
    return s


def _balanced_json(text: str, start: int) -> str | None:
    depth = 0
    quoted = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if escaped:
            escaped = False
            continue
        if ch == "\\":
            escaped = True
            continue
        if ch == '"':
            quoted = not quoted
            continue
        if quoted:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _decode_rsc(html: str) -> str:
    # Extract quoted payload chunks passed to self.__next_f.push([...]).
    chunks: list[str] = []
    for m in re.finditer(r"self\.__next_f\.push\(\[(.*?)\]\)", html, re.S):
        inside = m.group(1)
        comma = inside.find(",")
        if comma < 0:
            continue
        candidate = inside[comma + 1:].strip()
        if not candidate.startswith('"'):
            continue
        try:
            value = json.loads(candidate)
        except Exception:
            continue
        if isinstance(value, str):
            chunks.append(value)
    return "".join(chunks)


def _extract_players(html: str) -> list[dict]:
    stream = _decode_rsc(html)
    # Fall back to raw HTML because framework serialization can change while the
    # literal public player objects remain present.
    haystack = stream or html
    starts = [m.start() for m in re.finditer(r'\{"acnt":"\d{10}"', haystack)]
    seen: dict[str, dict] = {}
    for start in starts:
        raw = _balanced_json(haystack, start)
        if not raw:
            continue
        try:
            obj: dict[str, Any] = json.loads(raw)
        except Exception:
            continue
        acnt = str(obj.get("acnt") or "")
        team = obj.get("team") if isinstance(obj.get("team"), dict) else {}
        team_code = str(team.get("code") or "")[:3]
        if not acnt or team_code != DRAGONS_PREFIX:
            continue
        pos = str(obj.get("defendStation") or "")
        player = {
            "id": f"cpbl-{acnt}",
            "source_id": acnt,
            "name": str(obj.get("chName") or "").strip(),
            "name_en": str(obj.get("engname") or "").strip(),
            "number": str(obj.get("uniformNo") or ""),
            "position_group": POSITION.get(pos, ""),
            "position_code": pos,
            "active": not bool(obj.get("retiredDate")),
            "url": f"{BASE}/players/{acnt}",
            "source": "CPBL Stats",
        }
        # Do not emit a level here.  The schedule/lineup adapter can infer the
        # player's latest first-/second-team appearance and merge it later.
        old = seen.get(acnt, {})
        seen[acnt] = {**old, **{k: v for k, v in player.items() if v not in (None, "")}}
    return [p for p in seen.values() if p.get("name")]


def collect(config: dict) -> SourceResult:
    try:
        r = _session().get(f"{BASE}/players", timeout=30)
        r.raise_for_status()
        players = _extract_players(r.text)
        if not players:
            return SourceResult("cpbl_stats", "bad", {}, note="CPBL Stats roster payload was reachable but no WDragons players were parsed.")
        return SourceResult("cpbl_stats", "ok", {"players": players}, note=f"CPBL Stats 公開球員名單 {len(players)} 人")
    except Exception as exc:
        return SourceResult("cpbl_stats", "bad", {}, note="CPBL Stats roster request failed.", error=str(exc))
