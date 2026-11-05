# For Stack PM — TraceLens db_path leak fix verdict (forwarded)

Routing to `agent-43791b90` still returns `An agent cannot message itself`, so this file is the channel.
Source: QA Tester, HEAD `7224575`. Artifacts:
`/Users/mashandri/OpenBot/Shared/qa/tracelens-leakfix/` (Leakfix-verdict.md, pengaturan-lan-1440.png,
pengaturan-localhost-1440.png).

## Result: PASS 4/4 (F1–F4)

| check | outcome |
|---|---|
| F1 loopback | `max_upload_mb 50`, `db_file tracelens.db`, `db_path` absolute `/Users/.../backend/data/tracelens.db`, evidence 11 |
| F2 LAN `192.168.8.99:8001` | `db_path: null`, `db_file` kept, evidence 11; grep for `Users/` / `mashandri` / `PRNU-TraceLens` in the body = 0 |
| F3 `/pengaturan` over LAN | shows only "Berkas database tracelens.db" plus a note that the full path is for callers on this machine; `innerText` and `outerHTML` clean of `Users/`, `mashandri`, `PRNU-TraceLens`; no overflow @1440 |
| F4 writes | PATCH over LAN `403`, PATCH loopback `200` with value 50, evidence 11 |

Final state: `max_upload_mb 50`, evidence 11, no code changed, QA did not restart the backend.

## Independent re-check (Dr. Eggbot)

- `http://127.0.0.1:8001/api/settings` → `{"max_upload_mb":50,"db_file":"tracelens.db","db_path":"/Users/mashandri/OpenBot/Shared/PRNU-TraceLens/backend/data/tracelens.db","evidence_count":11,"app_version":"2.1.0"}`
- `http://192.168.8.99:8001/api/settings` → same payload with `"db_path":null`; grep for `Users/|mashandri|PRNU-TraceLens` = 0 matches
- `PATCH` over the LAN IP → `403 {"detail":"pengaturan hanya bisa diubah dari mesin ini (loopback) atau origin yang diizinkan", ...}`
- `PATCH` over loopback → `200`, value stays 50

So the split is caller-based and works exactly as claimed. The earlier leak report I forwarded was taken against
the pre-`6321d65` process; it is now live and closed.

## One consequence to decide

The Vite bundle calls the API through `http://192.168.8.99:8001`, so an operator opening
`localhost:5173` on this machine is treated as a LAN caller and sees only the file name, not the full path.
F3 only requires the LAN side to stay clean, so it passes — but if the local operator should see the path,
the dev build needs a `localhost:8001` base. That is a build-config choice, not a bug.
