# 龍隊情報台 / WDragons Intelligence v0.2.1

一套 **純前端、local-first、低維護** 的味全龍公開情報與本地狀態總覽工具。

核心邊界只有兩層：

1. **公開版**：盡可能集合公開賽程、比分、比賽結果、球員、近期先發陣容、官方消息與事件，全部放進同一條時間軸 / 行事曆。
2. **本地狀態層**：使用者自己匯入 CSV / XLSX / JSON 後，才解鎖「整隊 → 一二軍 → 位置 → 個人」快速狀態對照。資料只存在瀏覽器 IndexedDB，不上傳。

## v0.2.1 已完成

### 公開情報
- 一軍 / 二軍統一賽事 schema。
- 賽程、比分、比賽狀態、球場、先發投手、勝敗投、救援、MVP（來源有提供時）。
- 最近 14 日與次日 CPBL box 資料嘗試擷取，建立近期先發陣容脈絡。
- CPBL Stats 公開球員名單 collector。
- 味全龍官方 RSS / Atom collector，支援多 feed 去重。
- 公開來源健康狀態、最後檢查、最後成功時間。
- collector 失敗時保留最後成功快取，不會把網站清空。

### 行事曆 / 情報
- 月行事曆（日 → 六）。
- GAME / LINEUP / ROSTER / NEWS / LEAGUE / LOCAL 事件共用時間軸。
- 比賽卡可顯示比分與 FINAL / LIVE / SCHEDULED / POSTPONED 等狀態。
- 點日期看當日全部事件；點比賽看公開賽事脈絡。
- 全站搜尋球員與事件。

### 本地狀態總覽
- 匯入後自動辨識日期、球員、軍別、位置。
- 支援 long format (`metric`, `value`) 與 wide format。
- 團隊 → 一軍 / 二軍 → 位置 → 個人。
- 顯示最新值、簡單 Δ、近 7 日公開先發脈絡、下一場。

## 第一次使用

### A. 只預覽介面
直接開啟 `index.html`。


### B. 建立真實公開快取（建議）
Windows：雙擊

```text
refresh_public_data.bat
```

macOS / Linux：

```bash
./refresh_public_data.command
```

或手動：

```bash
python -m pip install -r requirements.txt
python collectors/run.py
```

完成後再開 `index.html`。`data/public-data.json` 與 `data/public-data.js` 會同步更新。

> CPBL 官方站可能限制部分雲端機房 IP，因此目前最穩定的設計是「台灣本機更新 → 保存快取 → GitHub Pages 顯示快取」。GitHub 自動排程先保留但不預設啟用。

## 本地資料匯入

進入「資料」→「選擇檔案」。支援 CSV / XLSX / JSON。

推薦至少有：

```text
analysis_date, player_name
```

選配：

```text
player_id, level, position
```

以及任意數值指標，例如：

```text
weight, pbf, smm, ffmi, ev_avg, ff_velo_kmh
```

或：

```text
analysis_date,player_name,metric,value,unit
```

匯入檔案只寫入瀏覽器 IndexedDB。它不會被寫回 `data/`、GitHub 或任何網路服務。

## 公開來源現況

| 來源 | 目前狀態 | 取得方式 | 用途 |
|---|---|---|---|
| CPBL 官方站 | 已接 | 公開頁面 token + public JSON/XHR | 一、二軍賽程、比分、結果、近期先發 |
| CPBL Stats | 已接 | 公開球員頁的網站資料 | 公開球員 identity / 位置 |
| 味全龍官網 | 已接 | RSS / Atom（失敗時保留舊快取） | 官方消息 |
| 一般新聞 | generic RSS 已完成、預設關閉 | RSS / Atom | GitHub 上線後再挑來源 |

## GitHub Pages

建立 repo 後，把本資料夾內容放在 repository root：

1. `Settings → Pages`
2. `Deploy from a branch`
3. `main / (root)`

不需要 Node、Vite、React 或 build pipeline。

`.github/workflows/refresh-public-data.yml` 目前只開 `workflow_dispatch`，排程刻意關閉。CPBL 是否能從 GitHub Actions 抓取，要等 repo 建立後實測；若被擋，就維持本機更新後 `git push data/` 的策略。

## 檔案結構

```text
index.html
assets/
  css/styles.css
  js/app.js
collectors/
  run.py
  sources/
    cpbl.py
    cpbl_stats.py
    rss.py
config/sources.json
data/
  public-data.json
  public-data.js
samples/
  local_overlay_sample.csv
  public_demo_data.json
docs/
.github/workflows/
refresh_public_data.bat
refresh_public_data.command
requirements.txt
```
