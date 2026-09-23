# Source matrix — v0.2

| Domain | Source | Auth | v0.2 | Failure behavior |
|---|---|---:|---:|---|
| 一軍賽程 / 比分 | CPBL official | none | ON | keep last good cache |
| 二軍賽程 / 比分 | CPBL official | none | ON | keep last good cache |
| 近期先發陣容 | CPBL box public data | none | ON | schedule remains usable |
| 公開球員 | stats.cpbl.com.tw | none | ON | keep last good roster |
| 球隊官方消息 | wdragons.com RSS/Atom | none | ON | keep last good news |
| 一般新聞 | generic RSS | none | READY/OFF | enable feeds later |
| 球員異動 | CPBL public page | none | NEXT | add only after stable contract verified |
| Internal BC/performance | user local file | none | LOCAL ONLY | never publish |

## CPBL deployment note

CPBL public pages may reject requests from some cloud data-center IP ranges. Therefore v0.2 treats the static public bundle as the runtime source of truth and makes collectors replace/update that bundle out-of-band.

Recommended sequence:

```text
Taiwan/local machine collector
        ↓
data/public-data.json + .js
        ↓
git push
        ↓
GitHub Pages
```

GitHub Actions is included as a manual experiment, not a required dependency.

## Acceptance rule for future sources

Add a source only when it materially improves one of these questions:

- What is happening to the team now?
- What changed recently?
- When is the next relevant event/game?
- What public context helps interpret a local status change?

Reject sources that mainly add complexity, credentials, billing, brittle scraping or duplicated information.
