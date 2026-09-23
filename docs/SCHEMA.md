# Normalized schema — v0.2

## `games[]`

```json
{
  "id": "cpbl-2026-A-123",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "level": "一軍|二軍",
  "away_team": "...",
  "home_team": "...",
  "away_score": 0,
  "home_score": 0,
  "venue_id": "v-...",
  "status": "SCHEDULED|LIVE|FINAL|POSTPONED|SUSPENDED|CANCELLED|RESUMED",
  "away_starter": "optional",
  "home_starter": "optional",
  "winning_pitcher": "optional",
  "losing_pitcher": "optional",
  "save_pitcher": "optional",
  "mvp": "optional",
  "source": "CPBL",
  "url": "original public URL"
}
```

## `lineups[]`

```json
{
  "id": "lineup-...",
  "date": "YYYY-MM-DD",
  "game_id": "...",
  "level": "一軍|二軍",
  "team": "味全龍",
  "players": ["九名打者 + 先發投手（若可取得）"],
  "batting_order": ["1棒", "..."],
  "starter_pitcher": "optional",
  "source": "CPBL"
}
```

`players` 是狀態總覽計算近期公開「先發脈絡」使用的集合；它不是總出賽量、PA、局數或 workload 指標。

## `players[]`

```json
{
  "id": "cpbl-<public account id>",
  "source_id": "public account id",
  "name": "...",
  "number": "...",
  "level": "optional; latest observed A/D lineup context",
  "position_group": "投手|捕手|內野手|外野手|...",
  "active": true,
  "url": "public player page"
}
```

## `events[]`

```json
{
  "id": "stable-key",
  "date": "YYYY-MM-DD",
  "time": "HH:MM",
  "type": "GAME|LINEUP|ROSTER|NEWS|LEAGUE|VENUE|LOCAL",
  "title": "human-readable fact",
  "summary": "short factual context",
  "source": "source name",
  "url": "optional original URL",
  "player_id": "optional",
  "player_ids": ["optional"],
  "game_id": "optional",
  "venue_id": "optional",
  "tags": ["optional"]
}
```

## `source_status[]`
`id`, `name`, `status`, `auth`, `mode`, `last_checked`, `last_success`, `records`, `note`.

## Local overlay

輸入 schema 刻意寬鬆。

Identity / context aliases：日期、球員、player_id、軍別、位置。

Metric 支援：
- wide format：每個 numeric column 自動成為 metric；
- long format：`metric` + `value` + optional `unit`。

瀏覽器 normalize 後增加：
`__date`, `__player`, `__player_id`, `__level`, `__position`, `__metrics`, `__source_file`。

原始欄位仍保留。資料只放 IndexedDB。
