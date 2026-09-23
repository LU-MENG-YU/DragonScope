# v0.3.0 — 公開情報恢復

- 新增一般「味全龍」新聞 RSS 聚合，保留原始媒體名稱。
- 恢復場館一級頁面與場館搜尋。
- 新增球場 registry，補充城市、室內外與天氣座標。
- 新增免金鑰 Open-Meteo 比賽天氣：溫度、濕度、降雨機率、風速。
- 天氣整合至下一場、行事曆與比賽詳細資訊。
- 修復 public-data 衝突標記；refresh workflow 改為 main 移動時重新產生資料。

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
