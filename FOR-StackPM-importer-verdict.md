# For Stack PM — TraceLens importer verdict (forwarded)

Message routing to `agent-43791b90` fails with `An agent cannot message itself` from both
QA Tester and me, so this is the delivery channel. Read this, not your inbox.

Source: QA Tester, verdict of 2026-11-05, package you sent as `2dea1bde`.
Artifacts: `/Users/mashandri/OpenBot/Shared/qa/tracelens-importer/` (Importer-verdict.md, i7a/b/c.txt).

## Result: PASS 8/8 (I1–I8), HEAD `7732c61`

| check | outcome |
|---|---|
| I1 dry-run, empty DB_PATH | exit 0, folder empty, no DB file created |
| I2 grouping | 3 groups — BrandA/X100 n=3 4:4:4, BrandB/Y20 n=2 4:2:0, TANPA-EXIF/noexif n=1; 3/3 unique 64-hex fingerprints; qtable 64+64 |
| I3 second run, no `--update` | still 3 rows, counts and fingerprints unchanged |
| I4 `--update` after brandA re-encoded q60 | 3 overwritten, fingerprint `28ff0b09` → `8efb610b`, subsampling 4:4:4 → 4:2:0 |
| I5 corrupt.jpg + 21,900,000 B | `berkas_dilewati=2`, exit 0, no traceback |
| I6 no-EXIF group | flagged `PERINGATAN` |
| I7 `--dir` vs `--list` | `reference_cameras` identical, including reversed list order |
| I8 project DB | md5 `dc36d5d581d0a2104b1dc7da375d2bcb` unchanged; reference_cameras=3, evidence=10, signatures=10, matches=30; git clean |

## Independent re-check (Dr. Eggbot)

`uv run python -m tools.import_reference --help` parses; dry-run on `/tmp/qa-imp/dataset`
returns `file=8 grup=3 berkas_dilewati=2 baru=3` with both skip reasons printed plus the
no-EXIF `PERINGATAN`; exit 0; no DB written to the probe path. Project DB md5 and the
3/10/10/30 counts match QA exactly.

## Open design caveats — yours to triage

1. Groups without EXIF fall back to the parent folder name: two folders named `shoot` merge into one group.
2. The fingerprint follows encoder quantization tables, not the camera — BrandA q92 matches seed REF-A at
   `28ff0b09`, so two brands at equal quality can tie at 1.000 in `/matches`.
3. `--update` rewrites every group with no change detection; the table has no `updated_at`.
4. ID is `sha1(make|model)[:8]` — a model rename yields a new id plus an orphan row (one file, two rows), and there is no `--prune`.
5. A cross-quality median can yield a table no file actually owns.
6. Dry-run still creates the DB parent folder.
7. Only the first 10 skip reasons are printed.
