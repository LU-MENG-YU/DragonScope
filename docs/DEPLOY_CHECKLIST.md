# Deployment checklist

## Before first public deploy

- [ ] Run `refresh_public_data.bat` (Windows) or `./refresh_public_data.command` (macOS/Linux).
- [ ] Confirm `data/public-data.json` changed from `EMPTY_CACHE` to `PUBLIC_CACHE`.
- [ ] Open `index.html` and confirm upcoming games / calendar are populated.
- [ ] Open 「資料來源」 and check CPBL / CPBL Stats / WDragons source health.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Run `python tests/smoke_test.py`.

## GitHub

- [ ] Upload repository contents; do **not** upload any private team dataset.
- [ ] Enable GitHub Pages from `main / root`.
- [ ] Manually run `Refresh public intelligence` workflow once.
- [ ] If CPBL reports blocked/bad but Pages works, keep Actions schedule disabled and update from local machine.
- [ ] Only enable a cron after several successful manual runs.

## Private data safety

- [ ] Internal BC / performance data never appears under `data/`, `samples/` or git history.
- [ ] Browser IndexedDB is the only default persistence for imported internal data.
- [ ] Exported local cache is handled as private data by the user.
