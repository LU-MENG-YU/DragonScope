# v0.2.1 — UI 文案精簡

- 移除介面中的產品原則、因果判定與使用方式說明文案。
- 未匯入本地資料時僅保留「本地狀態總覽未啟用」。
- 保留功能名稱、資料狀態、數量、日期與必要操作資訊。

# Changelog

## 0.2.0 — 2026-09-23

- Reframed product as **public team intelligence + optional local state overview**, not an analysis platform.
- Calendar promoted to first-class temporal index for games, scores, lineups, news and local measurement events.
- Added CPBL first-/second-team schedule, result and recent-lineup collector.
- Added CPBL Stats public player collector.
- Added multi-feed WDragons official RSS/Atom collector.
- Added last-known-good source behavior and source health panel.
- Removed fake public demo data from runtime bundle; first launch starts from an honest empty cache.
- Local state UI now unlocks only after import and supports arbitrary numeric metrics.
- Added team → squad → position → player navigation and public game-context alignment.
- Added local backup re-import support for normalized `__metrics` records.
- Simplified source surface by removing non-core weather/AQI scaffolds from this package.
- Added tests, deploy checklist, source matrix and technical provenance notes.
