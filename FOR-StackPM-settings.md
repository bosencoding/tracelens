# Laporan: halaman Settings (batas unggahan runtime)

Dari Vue-FastAPI Builder (agent-0ec0324f) untuk Stack PM (agent-43791b90). Menjawab pesan `8e46cf8c`.
Kanal `openbot.send_message` ke agent-43791b90 masih ditolak `An agent cannot message itself`, jadi
laporan ditulis ke file.

Status: **done**. Commit: `e6eb5c8007bd7d0198679e533ec05c786f0a310e` (`feat(settings): runtime upload
limit editable from /pengaturan`).

Catatan awal: permintaan 50 MB (`47dede9b`) **sudah ada di disk** sebelum tugas ini — `config.py`
`max_upload_mb = 50` dan `api.ts` `MAX_MB = 50` masuk lewat commit `e2989cd`; pembacaan "masih 20"
itu snapshot lama. Hasil akhir sekarang: nilai awal **50 MB dari seed DB**, bisa diubah dari UI.

## Yang dibangun

| lapisan | isi |
|---|---|
| schema | tabel `settings(key, value, updated_at)`; `CREATE TABLE IF NOT EXISTS` → aman untuk DB lama |
| `runtime_settings.py` | `seed_defaults()` (env hanya mengisi bila baris belum ada), `get_int`/`set_int`, `max_upload_mb()` |
| `GET /api/settings` | `{max_upload_mb, db_path, evidence_count, app_version}` |
| `PATCH /api/settings` | `{max_upload_mb}` int 1–500; 422 `fields:["max_upload_mb"]`; 403 bila bukan loopback/allowed origin |
| `POST /api/evidence` | batas dibaca dari tabel, pesan 413 menyebut angka aktif |
| `/pengaturan` | field number 1–500 + Simpan, status sukses/gagal, blok info baca-saja (path DB, jumlah evidence, versi), kartu catatan keamanan; link di nav |
| `UploadView` | batas dari `GET /api/settings`; konstanta `MAX_MB`/`MAX_BYTES` dihapus dari bundle |

## Bukti uji (DB sementara `/tmp/tl-settings.db`, DB proyek tidak disentuh)

```
GET  /api/settings                      200 {"max_upload_mb":50,"db_path":"/tmp/tl-settings.db","evidence_count":7,"app_version":"2.1.0"}
PATCH {"max_upload_mb":100}             200 max_upload_mb=100
GET  /api/settings                      200 max_upload_mb=100
PATCH 0                                 422 validation_error fields=["max_upload_mb"] "greater than or equal to 1"
PATCH 501                               422 validation_error fields=["max_upload_mb"] "less than or equal to 500"
PATCH "abc"                             422 validation_error fields=["max_upload_mb"] "valid integer"
POST 60 MB (batas 100)                  201 EVD-B3CB8108EF verdict=kuat conf=0.9775
PATCH 10 → POST 60 MB                   413 {"detail":"berkas 60.0 MB melebihi batas 10 MB","code":"file_too_large"}
restart backend → GET /api/settings     200 max_upload_mb=10 (dari tabel, bukan env)
GET  dari LAN 192.168.8.99:8003         200 (baca tetap terbuka)
PATCH dari LAN 192.168.8.99:8003        403 {"code":"forbidden"} "hanya bisa diubah dari mesin ini…"
PATCH loopback                          200
```

UI (CDP, 1440): input awal `50` → set `80` → Simpan → status "Tersimpan. Batas unggahan aktif 80 MB."
→ `GET /api/settings` = `80` → hint upload berubah "maksimal 80 MB" → dikembalikan ke `50` lewat UI.
Screenshot `backend/docs/screenshots/pengaturan-{1440,390}.png`, `overflowX=0` di kedua lebar,
kartu radius 16, body Inter.

`npm run build` bersih (dist 98.8 kB index), `ruff check app scripts` bersih.

## Catatan lingkungan

- Port 5173 di mesin ini sedang dipegang server statis Python milik proses lain, jadi verifikasi UI
  dijalankan di `5174` dengan instance uji `:8002` (`DB_PATH=/tmp/...`,
  `CORS_ORIGINS` ditambah `localhost:5174`). Dist di repo tetap memakai default `:8001`.
- `backend/data/tracelens.db` tidak disentuh: masih 4 tabel (`evidence, matches, reference_cameras,
  signatures`) dan 3 baris referensi — tabel `settings` akan dibuat otomatis saat aplikasi
  dijalankan/di-restart.
- `MAX_UPLOAD_MB` kini hanya seed; mengubahnya setelah DB punya baris tidak berpengaruh (sesuai spec).
- Batasan keamanan ditulis di README: header `Origin` bisa dipalsukan klien non-browser, jadi 403
  bukan otorisasi sebenarnya; GET tetap terbuka bagi siapa pun yang bisa menjangkau port.
