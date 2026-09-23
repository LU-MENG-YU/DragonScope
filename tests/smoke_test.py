from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / 'data/public-data.js').read_text(encoding='utf-8')
m = re.search(r'window\.WD_INTEL_DATA\s*=\s*(\{.*\})\s*;\s*$', text, re.S)
assert m, 'public-data.js bundle is not parseable'
d = json.loads(m.group(1))

for key in ['meta', 'players', 'venues', 'games', 'events', 'lineups', 'source_status']:
    assert key in d, f'missing top-level key: {key}'


def unique(items, label):
    ids = [x['id'] for x in items]
    assert len(ids) == len(set(ids)), f'duplicate {label} ids'


for key in ['players', 'venues', 'games', 'events', 'lineups']:
    unique(d[key], key)

players = {x['id'] for x in d['players']}
venues = {x['id'] for x in d['venues']}
games = {x['id'] for x in d['games']}
allowed = {'SCHEDULED', 'LIVE', 'FINAL', 'POSTPONED', 'SUSPENDED', 'CANCELLED', 'RESUMED'}

for g in d['games']:
    assert g['status'] in allowed, f'unknown game status: {g["status"]}'
    assert g.get('date'), f'missing date in {g["id"]}'
    if g.get('venue_id'):
        assert g['venue_id'] in venues, f'unknown venue in game {g["id"]}'

for e in d['events']:
    if e.get('game_id'):
        assert e['game_id'] in games, f'unknown game ref: {e["id"]}'
    if e.get('venue_id'):
        assert e['venue_id'] in venues, f'unknown venue ref: {e["id"]}'
    if e.get('player_id'):
        assert e['player_id'] in players, f'unknown player ref: {e["id"]}'
    for x in e.get('player_ids', []):
        assert x in players, f'unknown player ref in {e["id"]}'

for lineup in d['lineups']:
    if lineup.get('game_id'):
        assert lineup['game_id'] in games, f'unknown lineup game ref: {lineup["id"]}'

print(f'OK: {len(d["players"])} players, {len(d["games"])} games, {len(d["events"])} events, {len(d["lineups"])} lineups')
