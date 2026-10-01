from __future__ import annotations

import json, urllib.parse, urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta
from collectors.common import SourceResult, stable_key

API="https://api.open-meteo.com/v1/forecast"
SOURCE_URL="https://open-meteo.com/"

def _wmo_text(code):
    try: code=int(code)
    except Exception: return ""
    if code==0: return "晴"
    if code in {1,2}: return "晴時多雲"
    if code==3: return "陰"
    if code in {45,48}: return "霧"
    if code in {51,53,55,56,57}: return "毛毛雨"
    if code in {61,63,65,66,67,80,81,82}: return "雨"
    if code in {71,73,75,77,85,86}: return "雪"
    if code in {95,96,99}: return "雷雨"
    return ""

def _nearest_hour_index(times, day, start_time):
    if not times: return None
    try:
        p=str(start_time or "18:00").split(":"); hh=int(p[0]); mm=int(p[1]) if len(p)>1 else 0
    except Exception:
        hh,mm=18,0
    target=datetime.fromisoformat(f"{day}T{hh:02d}:{mm:02d}")
    best=None
    for i,raw in enumerate(times):
        try: dt=datetime.fromisoformat(raw)
        except Exception: continue
        delta=abs((dt-target).total_seconds())
        if best is None or delta<best[0]: best=(delta,i)
    return None if best is None else best[1]

def _forecast(lat,lon,days):
    params={
        "latitude":lat,"longitude":lon,
        "hourly":"temperature_2m,relative_humidity_2m,precipitation_probability,precipitation,weather_code,wind_speed_10m,wind_gusts_10m",
        "timezone":"Asia/Taipei","forecast_days":max(1,min(int(days or 16),16))
    }
    url=API+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"DragonScope/0.3 weather collector"})
    with urllib.request.urlopen(req,timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))

def _event(game,venue,fc):
    h=fc.get("hourly") or {}; idx=_nearest_hour_index(h.get("time") or [],game.get("date"),game.get("start_time"))
    if idx is None: return None
    def val(k):
        a=h.get(k) or []; return a[idx] if idx<len(a) else None
    temp,rh,pop,precip,wind,gust,code=[val(k) for k in ("temperature_2m","relative_humidity_2m","precipitation_probability","precipitation","wind_speed_10m","wind_gusts_10m","weather_code")]
    cond=_wmo_text(code); bits=[]
    if cond: bits.append(cond)
    if temp is not None: bits.append(f"{temp}°C")
    if pop is not None: bits.append(f"降雨 {pop}%")
    if rh is not None: bits.append(f"濕度 {rh}%")
    if wind is not None: bits.append(f"風 {wind} km/h")
    matchup=f"{game.get('away_team','')} vs {game.get('home_team','')}".strip()
    return {
        "id":stable_key("weather",game.get("id"),prefix="e"),
        "date":game.get("date",""),"time":game.get("start_time",""),"type":"WEATHER",
        "title":f"比賽天氣 · {matchup}","summary":" · ".join(bits),"source":"Open-Meteo","url":SOURCE_URL,
        "game_id":game.get("id"),"venue_id":game.get("venue_id"),
        "weather":{"mode":"FORECAST","condition":cond,"temperature_c":temp,"relative_humidity_pct":rh,
          "precipitation_probability_pct":pop,"precipitation_mm":precip,"wind_speed_kmh":wind,
          "wind_gusts_kmh":gust,"weather_code":code,"forecast_time":(h.get("time") or [""])[idx]},
        "tags":["FORECAST",venue.get("name","")]
    }

def collect(config: dict, data: dict | None=None) -> SourceResult:
    data=data or {}; venues={v.get("id"):v for v in data.get("venues",[]) if v.get("id")}
    today=date.today(); horizon=today+timedelta(days=max(1,min(int(config.get("forecast_days",16)),16)))
    games=[g for g in data.get("games",[]) if g.get("date") and today.isoformat()<=g["date"]<=horizon.isoformat()
           and g.get("status") not in {"FINAL","POSTPONED","CANCELLED"} and g.get("venue_id") in venues]
    byv=defaultdict(list)
    for g in games:
        v=venues[g["venue_id"]]
        if not v.get("indoor") and v.get("latitude") is not None and v.get("longitude") is not None:
            byv[g["venue_id"]].append(g)
    events=[]; errors=[]
    for vid,vg in byv.items():
        v=venues[vid]
        try:
            fc=_forecast(v["latitude"],v["longitude"],config.get("forecast_days",16))
            for g in vg:
                e=_event(g,v,fc)
                if e: events.append(e)
        except Exception as exc:
            errors.append(f"{v.get('name',vid)}: {exc}")
    if events:
        return SourceResult("weather","warn" if errors else "ok",{"events":events},note=f"{len(events)} 場比賽天氣",error="; ".join(errors[:2]) or None)
    return SourceResult("weather","warn",{},note="目前預報範圍內沒有可配對的戶外比賽",error="; ".join(errors[:2]) or None)
