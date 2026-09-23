from __future__ import annotations

import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

from collectors.common import SourceResult, stable_key


def _clean(value: str) -> str:
    value = html.unescape(value or "")
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _first_text(node: ET.Element, names: tuple[str, ...]) -> str:
    for child in list(node):
        local = child.tag.rsplit("}", 1)[-1]
        if local in names:
            return (child.text or "").strip()
    return ""


def _date_parts(raw: str) -> tuple[str, str]:
    if not raw:
        return "", ""
    try:
        dt = parsedate_to_datetime(raw).astimezone()
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone()
        return dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M")
    except Exception:
        return raw[:10] if re.match(r"\d{4}-\d{2}-\d{2}", raw) else "", ""


def collect_feed(url: str, source_id: str = "news", source_label: str | None = None) -> SourceResult:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 WDragonsIntelligence/0.2 public-feed-reader",
                "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml, */*",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read()
        root = ET.fromstring(raw)
        items = root.findall(".//item")
        if not items:
            items = [x for x in root.iter() if x.tag.rsplit("}", 1)[-1] == "entry"]

        events: list[dict] = []
        for item in items[:100]:
            title = _first_text(item, ("title",))
            pub = _first_text(item, ("pubDate", "published", "updated"))
            desc = _first_text(item, ("description", "summary", "content"))\n            publisher = _clean(_first_text(item, ("source",)))
            link = _first_text(item, ("link",))
            if not link:
                for child in list(item):
                    if child.tag.rsplit("}", 1)[-1] == "link" and child.attrib.get("href"):
                        link = child.attrib["href"]
                        break
            day, tm = _date_parts(pub)
            title = _clean(title)
            if not title:
                continue
            events.append({
                "id": stable_key(source_id, link or title, prefix="e"),
                "date": day,
                "time": tm,
                "type": "NEWS",
                "title": title,
                "summary": _clean(desc)[:420],
                "url": link,
                "source": source_label or source_id,
                "tags": ["官方" if source_id == "wdragons" else "RSS"],
            })
        if not events:
            return SourceResult(source_id, "bad", {}, note=f"Feed reachable but no entries parsed: {url}")
        return SourceResult(source_id, "ok", {"events": events}, note=f"RSS/Atom: {url}")
    except Exception as exc:
        return SourceResult(source_id, "bad", {}, note=f"Feed failed: {url}", error=str(exc))


def collect(config: dict) -> SourceResult:
    source_id = config.get("source_id", "news")
    source_label = config.get("name") or source_id
    feeds = config.get("feeds") or []
    if not feeds:
        return SourceResult(source_id, "warn", {}, note="No RSS feeds configured.")

    by_id: dict[str, dict] = {}
    errors: list[str] = []
    ok_feeds = 0
    for url in feeds:
        result = collect_feed(url, source_id, source_label)
        if result.status == "ok":
            ok_feeds += 1
        for event in result.payload.get("events", []):
            by_id[event["id"]] = event
        if result.error or result.status == "bad":
            errors.append(result.error or result.note)

    merged = list(by_id.values())
    status = "ok" if merged and not errors else ("warn" if merged else "bad")
    note = f"{ok_feeds}/{len(feeds)} feed(s)；{len(merged)} 則"
    return SourceResult(source_id, status, {"events": merged}, note=note, error="; ".join(errors[:2]) or None)
