# For Stack PM — TraceLens thumbnail verdict (forwarded)

Routing to `agent-43791b90` still returns `An agent cannot message itself`, so this file is the channel.
Source: QA Tester, verdict taken at HEAD `5b45ab4`, target `EVD-492EA1F116` (04.jpg, 15,954,685 B).
Artifacts: `/Users/mashandri/OpenBot/Shared/qa/tracelens-thumbnail/` (Thumbnail-verdict.md + 5 screenshots).

## Result: PASS 7/7 (B1–B7)

| check | outcome |
|---|---|
| B1 `/hasil` | img 480×320, displayed 318×239 inside aspect-[4/3] container, no layout shift; label `04.jpg 6240×4160 15.22 MB 4:2:2`; "Lihat ukuran penuh" → `/image` |
| B2 headers | `HEAD /image` 200 image/jpeg len 15954685; `HEAD /thumbnail` 200 image/jpeg 47904 + `cache-control private,max-age=3600`; bogus id → 404 `{detail,code}` |
| B3 integrity | sha256 disk = DB = `GET /image` = after 3× `/thumbnail` (`492ea1f1…`); uploads dir unchanged |
| B4 missing file | `/tmp` instance (8002 + Vite 5174): file deleted → `410 file_missing`, `/hasil` still renders "pratinjau tidak tersedia", no 500 |
| B5 caching | ETag = sha256, `If-None-Match` → `304`, `Content-Length` = byte_size |
| B6 hostile ids | bogus and traversal → 404, no absolute path in the body |
| B7 list | `/` renders 11 rows, img 40×40; rows without a file still render with an empty slot |

Final state: evidence 11, `max_upload_mb=50`, sha256 unchanged, test instance stopped, `/tmp/qa-thumb`
removed, no code changed.

## Independent re-check (Dr. Eggbot)

- `GET /thumbnail` for `EVD-492EA1F116` → `200`, `image/jpeg`, `47904` bytes
- headers: `cache-control: private, max-age=3600`, `etag: "492ea1f1…6b85"` (sha256), `content-length: 47904`
- `If-None-Match` with that ETag → `304`
- `NOPE/thumbnail` → `404 {"detail":"bukti NOPE tidak ditemukan","code":"not_found"}`
- `..%2f..%2fetc%2fpasswd/thumbnail` → `404 {"detail":"Not Found","code":"not_found"}`, no path echoed
- `HEAD /image` → `200`, `image/jpeg`

## Two things that moved after QA's run

1. **HEAD drift.** QA tested `5b45ab4`; repo is now `7224575`. The only commits in between are
   `6321d65 fix(settings): stop leaking the absolute database path to LAN callers` and its docs commit.
   Files touched: `models.py`, `routes_settings.py`, `types.ts`, `SettingsView.vue`, `UploadView.vue`,
   README, screenshots. No thumbnail or image route touched, so B1–B7 still hold — but the verdict
   technically predates HEAD.
2. **The settings fix is committed, not live.** The running uvicorn still returns
   `db_path: "/Users/.../backend/data/tracelens.db"` because the process predates `6321d65`.
   Restart the backend to activate it; until then the leak is still on the LAN.

## Notes to triage

- Thumbnail slot with no file renders as a bare box, no placeholder icon.
- Console `ORB` error when a file is missing.
- `410 file_missing` is not surfaced in the UI.
- Thumbnail URLs in the bundle use the LAN base `192.168.8.99:8001` — check that this is intended for
  the demo network, and that it is not baked into a build that ships elsewhere.
