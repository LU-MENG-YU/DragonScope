"""CPBL public schedule / result / lineup collector.

This adapter only uses resources served by the public CPBL web site.  It keeps
all CPBL-specific request details in one file so a future site change does not
leak into the UI or local/private data layer.

The collector is deliberately fail-open at the orchestrator level: if CPBL is
unreachable, the last successful static bundle remains usable.
"""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

import requests

from collectors.common import SourceResult, stable_key

BASE = "https://www.cpbl.com.tw"
DRAGONS_PREFIX = "AAA"
KINDS = {"A": "一軍", "D": "二軍"}
TEAM_NAMES = {
    "AAA": "味全龍",
    "ACN": "中信兄弟",
    "ADD": "統一7-ELEVEn獅",
    "AJL": "樂天桃猿",
    "AEO": "富邦悍將",
    "AKP": "台鋼雄鷹",
}
POSITION_GROUP = {
    "1": "投手", "P": "投手",
    "2": "捕手", "C": "捕手",
    "3": "內野手", "4": "內野手", "5": "內野手", "6": "內野手",
    "1B": "內野手", "2B": "內野手", "3B": "內野手", "SS": "內野手",
    "7": "外野手", "8": "外野手", "9": "外野手",
    "LF": "外野手", "CF": "外野手", "RF": "外野手",
    "10": "指定打擊", "DH": "指定打擊",
}


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "X-Requested-With": "XMLHttpRequest",
    })
    return s


def _team_code(value: Any) -> str:
    return str(value or "")[:3]


def _team_name(code: str, fallback: str | None = None) -> str:
    return TEAM_NAMES.get(code, (fallback or code or "未知球隊"))


def _date(value: Any) -> str:
    text = str(value or "")
    m = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", text)
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else ""


def _time(value: Any) -> str:
    text = str(value or "")
    m = re.search(r"(?:T|\s)(\d{2}):(\d{2})", text)
    return f"{m.group(1)}:{m.group(2)}" if m else ""


def _token(s: requests.Session) -> str:
    r = s.get(f"{BASE}/schedule", timeout=25)
    r.raise_for_status()
    m = re.search(r"RequestVerificationToken:\s*'([^']+)'", r.text)
    if not m:
        raise RuntimeError("CPBL RequestVerificationToken not found (page changed or request blocked)")
    return m.group(1)


def _schedule(s: requests.Session, year: int, kind: str) -> list[dict]:
    token = _token(s)
    r = s.post(
        f"{BASE}/schedule/getgamedatas",
        data={"calendar": f"{year}/01/01", "location": "", "kindCode": kind},
        headers={"RequestVerificationToken": token, "Referer": f"{BASE}/schedule"},
        timeout=40,
    )
    r.raise_for_status()
    payload = r.json()
    if not payload.get("Success"):
        raise RuntimeError(f"CPBL schedule returned Success=false for kind={kind}")
    raw = payload.get("GameDatas", [])
    if isinstance(raw, str):
        raw = json.loads(raw)
    return raw if isinstance(raw, list) else []


def _status(g: dict, today: date) -> str:
    dtext = _date(g.get("GameDate"))
    try:
        gd = date.fromisoformat(dtext)
    except Exception:
        gd = today
    code = str(g.get("GameStatus") or "")
    chi = str(g.get("GameStatusChi") or "")
    stopped = str(g.get("IsGameStop") or "0") == "1"
    reserve = bool(g.get("ReserveDate"))
    win = bool(g.get("WinningPitcherName"))
    vs, hs = g.get("VisitingScore"), g.get("HomeScore")

    if "取消" in chi:
        return "CANCELLED"
    if "保留" in chi or "延" in chi or stopped or reserve:
        return "POSTPONED"
    if "結束" in chi or code == "3" or win:
        return "FINAL"
    if gd < today and (vs is not None or hs is not None):
        return "FINAL"
    if gd < today:
        return "POSTPONED"
    if gd == today and code not in {"", "0", "1"}:
        return "LIVE"
    return "SCHEDULED"


def _venue(raw_name: Any) -> tuple[str, dict]:
    name = str(raw_name or "未知球場").strip() or "未知球場"
    vid = stable_key(name, prefix="v")
    return vid, {"id": vid, "name": name, "source": "CPBL"}


def _game_url(year: int, kind: str, game_sno: Any) -> str:
    # The query form is intentionally simple; if CPBL changes the box route the
    # static record remains useful even when this navigation link becomes stale.
    return f"{BASE}/box?year={year}&kindCode={kind}&gameSno={game_sno}"


def _normalize_game(g: dict, *, year: int, kind: str, level: str, today: date) -> tuple[dict, dict, dict]:
    away_code, home_code = _team_code(g.get("VisitingTeamCode")), _team_code(g.get("HomeTeamCode"))
    away = _team_name(away_code, g.get("VisitingTeamName"))
    home = _team_name(home_code, g.get("HomeTeamName"))
    day = _date(g.get("GameDate"))
    start = _time(g.get("PreExeDate") or g.get("GameDateTimeS"))
    game_sno = g.get("GameSno")
    gid = f"cpbl-{year}-{kind}-{game_sno}"
    vid, venue = _venue(g.get("FieldAbbe"))
    status = _status(g, today)
    game = {
        "id": gid,
        "source_id": str(g.get("Pkno") or game_sno or gid),
        "source": "CPBL",
        "date": day,
        "start_time": start,
        "level": level,
        "kind_code": kind,
        "game_sno": game_sno,
        "season_half": str(g.get("GameSeasonCode") or ""),
        "away_team": away,
        "home_team": home,
        "away_team_code": away_code,
        "home_team_code": home_code,
        "away_score": g.get("VisitingScore"),
        "home_score": g.get("HomeScore"),
        "venue_id": vid,
        "venue_name": venue["name"],
        "status": status,
        "away_starter": g.get("VisitingPitcherName") or g.get("VisitingFirstMover") or "",
        "home_starter": g.get("HomePitcherName") or g.get("HomeFirstMover") or "",
        "winning_pitcher": g.get("WinningPitcherName") or "",
        "losing_pitcher": g.get("LoserPitcherName") or g.get("LosePitcherName") or "",
        "save_pitcher": g.get("CloserName") or g.get("CloserPitcherName") or "",
        "mvp": g.get("MvpName") or "",
        "url": _game_url(year, kind, game_sno),
    }
    if status == "FINAL" and game["away_score"] is not None and game["home_score"] is not None:
        title = f"{away} {game['away_score']} : {game['home_score']} {home}"
    else:
        title = f"{away} vs {home}"
    summary_bits = [status, level, venue["name"]]
    if game["winning_pitcher"]:
        summary_bits.append(f"勝 {game['winning_pitcher']}")
    if game["mvp"]:
        summary_bits.append(f"MVP {game['mvp']}")
    event = {
        "id": f"event-{gid}",
        "date": day,
        "time": start,
        "type": "GAME",
        "title": title,
        "summary": " · ".join(x for x in summary_bits if x),
        "source": "CPBL",
        "url": game["url"],
        "game_id": gid,
        "venue_id": vid,
        "tags": [level, status, "主場" if home_code == DRAGONS_PREFIX else "客場"],
    }
    return game, venue, event


def _getlive(s: requests.Session, *, year: int, kind: str, game_sno: Any) -> dict:
    r = s.post(
        f"{BASE}/box/getlive",
        data={"GameSno": str(game_sno), "Year": str(year), "KindCode": kind},
        headers={"Referer": f"{BASE}/box"},
        timeout=25,
    )
    r.raise_for_status()
    payload = r.json()
    # Most current payloads expose these as parsed arrays; historical responses
    # sometimes wrap them as JSON strings.
    out: dict[str, Any] = {}
    for key in ("GameDetailJson", "FirstSnoJson"):
        value = payload.get(key)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except Exception:
                value = None
        out[key] = value
    return out


def _lineup_payload(live: dict, game: dict) -> tuple[list[dict], list[dict], list[dict]]:
    rows = live.get("FirstSnoJson")
    if not isinstance(rows, list):
        rows = []

    dragon_rows = [r for r in rows if _team_code(r.get("TeamNo")) == DRAGONS_PREFIX]
    hitters = sorted(
        [r for r in dragon_rows if 1 <= int(r.get("Lineup") or 0) <= 9],
        key=lambda r: int(r.get("Lineup") or 99),
    )
    pitcher_rows = [r for r in dragon_rows if str(r.get("DefendStation") or r.get("DefendStationCode") or "") in {"1", "P"}]
    starter_pitcher = pitcher_rows[0].get("CHName") if pitcher_rows else ""
    names = [str(r.get("CHName") or "").strip() for r in hitters if r.get("CHName")]
    if starter_pitcher and starter_pitcher not in names:
        names.append(str(starter_pitcher).strip())

    if not names:
        # Future games can expose the announced starter via GameDetailJson even
        # before the full batting order exists.
        detail = live.get("GameDetailJson")
        if isinstance(detail, list) and detail:
            d = detail[0] or {}
            dragon_is_away = game.get("away_team_code") == DRAGONS_PREFIX
            p = d.get("VisitingFirstMover") if dragon_is_away else d.get("HomeFirstMover")
            if p:
                names = [str(p).strip()]
                starter_pitcher = str(p).strip()

    if not names:
        return [], [], []

    lid = f"lineup-{game['id']}-dragons"
    lineup = {
        "id": lid,
        "date": game["date"],
        "time": game.get("start_time", ""),
        "game_id": game["id"],
        "level": game["level"],
        "team": "味全龍",
        "players": names,
        "batting_order": [str(r.get("CHName") or "").strip() for r in hitters if r.get("CHName")],
        "starter_pitcher": starter_pitcher,
        "source": "CPBL",
    }
    event = {
        "id": f"event-{lid}",
        "date": game["date"],
        "time": game.get("start_time", ""),
        "type": "LINEUP",
        "title": f"味全龍 {game['level']} 先發陣容",
        "summary": "、".join(names[:10]),
        "source": "CPBL",
        "url": game.get("url", ""),
        "game_id": game["id"],
        "venue_id": game.get("venue_id", ""),
        "tags": [game["level"], "先發陣容"],
    }

    players: list[dict] = []
    for r in dragon_rows:
        acnt = str(r.get("Acnt") or "").strip()
        name = str(r.get("CHName") or "").strip()
        if not acnt or not name:
            continue
        station = str(r.get("DefendStation") or r.get("DefendStationCode") or "")
        players.append({
            "id": f"cpbl-{acnt}",
            "source_id": acnt,
            "name": name,
            "number": str(r.get("UniformNo") or ""),
            "level": game["level"],
            "position_group": POSITION_GROUP.get(station, ""),
            "active": True,
            "url": f"https://stats.cpbl.com.tw/players/{acnt}",
            "source": "CPBL",
            "last_public_appearance": game["date"],
        })
    return [lineup], [event], players


def collect(config: dict) -> SourceResult:
    year = int(config.get("year") or datetime.now().year)
    recent_lineup_days = int(config.get("recent_lineup_days", 14))
    delay = float(config.get("request_delay", 0.15))
    s = _session()
    today = datetime.now(timezone(timedelta(hours=8))).date()

    games: list[dict] = []
    venues: dict[str, dict] = {}
    events: list[dict] = []
    lineups: list[dict] = []
    players_by_id: dict[str, dict] = {}
    warnings: list[str] = []

    for kind, level in KINDS.items():
        try:
            raw_games = _schedule(s, year, kind)
        except Exception as exc:
            warnings.append(f"{level}賽程失敗: {exc}")
            continue
        for raw in raw_games:
            away_code, home_code = _team_code(raw.get("VisitingTeamCode")), _team_code(raw.get("HomeTeamCode"))
            if DRAGONS_PREFIX not in {away_code, home_code}:
                continue
            game, venue, event = _normalize_game(raw, year=year, kind=kind, level=level, today=today)
            if not game["date"]:
                continue
            games.append(game)
            venues[venue["id"]] = venue
            events.append(event)

        # Fetch full batting order only around the current date. This gives the
        # UI enough context for recent workload without hundreds of box calls.
        for game in [g for g in games if g["kind_code"] == kind]:
            try:
                gd = date.fromisoformat(game["date"])
            except Exception:
                continue
            if not (today - timedelta(days=recent_lineup_days) <= gd <= today + timedelta(days=1)):
                continue
            try:
                live = _getlive(s, year=year, kind=kind, game_sno=game["game_sno"])
                ls, es, ps = _lineup_payload(live, game)
                lineups.extend(ls)
                events.extend(es)
                for p in ps:
                    prev = players_by_id.get(p["id"], {})
                    incoming = {k: v for k, v in p.items() if v not in (None, "")}
                    if not prev or incoming.get("last_public_appearance", "") >= prev.get("last_public_appearance", ""):
                        players_by_id[p["id"]] = {**prev, **incoming}
                    else:
                        # Older appearance may still fill identity/position fields,
                        # but it must not move the observed squad level backwards.
                        safe = {k: v for k, v in incoming.items() if k not in {"level", "last_public_appearance"}}
                        players_by_id[p["id"]] = {**safe, **prev}
            except Exception as exc:
                warnings.append(f"{level} {game['date']} G{game['game_sno']} lineup: {exc}")
            time.sleep(delay)

    if not games:
        return SourceResult("cpbl", "bad", {}, note="No WDragons CPBL schedule was collected.", error="; ".join(warnings[:3]) or None)

    status = "warn" if warnings else "ok"
    note = f"CPBL {year}: 味全一、二軍 {len(games)} 場；近期先發 {len(lineups)} 場"
    if warnings:
        note += f"；{len(warnings)} 個非致命警告"
    return SourceResult(
        "cpbl",
        status,
        {
            "players": list(players_by_id.values()),
            "venues": list(venues.values()),
            "games": games,
            "events": events,
            "lineups": lineups,
        },
        note=note,
        error="; ".join(warnings[:2]) or None,
    )
