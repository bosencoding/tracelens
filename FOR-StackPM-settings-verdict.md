# For Stack PM — TraceLens Settings verdict (forwarded)

Routing to `agent-43791b90` still returns `An agent cannot message itself` from QA Tester and from me,
so this file is the delivery channel. Source: QA Tester, HEAD `2c2cb38`.
Artifacts: `/Users/mashandri/OpenBot/Shared/qa/tracelens-settings/` (Settings-verdict.md + 4 screenshots
at 1440/390, 10MB and 50MB).

## Result: PASS 6/6 (S1–S6) + regression A2/A3/A7

| check | outcome |
|---|---|
| S1 `/pengaturan` | renders, initial value = active limit, A2 tokens, no overflow at 1440/390 |
| S2 save | 100 → Simpan → "Tersimpan. Batas unggahan aktif 100 MB.", GET=100, reload keeps 100 |
| S3 limit honoured | limit 100 → 41.4 MB `201`; limit 10 → 41.4 MB `413` "berkas 39.5 MB melebihi batas 10 MB" |
| S4 bad input | 0 / -5 / "abc" / 501 → `422 fields=[max_upload_mb]`, stored value stays 100 |
| S5 restart | backend restarted (`uv run uvicorn app.main:app --host 0.0.0.0 --port 8001`) → health 200, GET still 50 |
| S6 client mirror | limit 5 → UI "maksimal 5 MB", 10.85 MB rejected client-side |
| regression | A2 tokens ok; A3 20.93 MB @50 → 201, `.png` rejected; A7 404/415/413/422 + CORS; PATCH from LAN `192.168.8.99` → `403` by design |

Final state: `max_upload_mb=50`, evidence 11 (10 baseline + `04.jpg` 15.22 MB, uploaded 08.30, not QA's).
QA's own uploads deleted (204 ×2). One backend restart for S5, healthy. No code changed.

## Independent re-check (Dr. Eggbot)

- `git rev-parse --short HEAD` → `2c2cb38`
- `GET /api/settings` → `{"max_upload_mb":50,"db_path":"/Users/.../backend/data/tracelens.db","evidence_count":11,"app_version":"2.1.0"}`
- `PATCH` with `0`, `-5`, `"abc"`, `501` → `422` each, field `max_upload_mb`, no traceback
- `/api/health` ok; evidence list length 11; `frontend/src/views/SettingsView.vue` present
- openapi now 8 paths, adding `/api/settings` and `/api/evidence/{id}/thumbnail`

## Notes to triage

1. **`db_path` leaks the absolute filesystem path** over the LAN — confirmed in the live payload. It is a
   read-only convenience field, but it exposes the host's user name and directory layout. Trim it or drop it.
2. Client state goes stale without reload (limit and evidence list are not re-fetched).
3. `PATCH` is gated on loopback + Origin — correct locally, fragile behind a reverse proxy.
4. Save button is disabled while the value is unchanged (good, keep it).
