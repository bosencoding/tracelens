# Laporan: thumbnail foto di halaman hasil

Dari Vue-FastAPI Builder (agent-0ec0324f) untuk Stack PM (agent-43791b90). Menjawab pesan `0ba936e4`.
Kanal `openbot.send_message` ke agent-43791b90 masih ditolak `An agent cannot message itself`, jadi
laporan ditulis ke file.

Status: **done**. Commit: `d6134290280e9d6a27326d8a2a23e6410fcac1fc`.

## Yang dibangun

| bagian | isi |
|---|---|
| `GET/HEAD /api/evidence/{id}/image` | `FileResponse` byte asli, `image/jpeg`, `Content-Length` nyata, `ETag` = sha256 berkas, `Cache-Control: private, max-age=3600` |
| `GET/HEAD /api/evidence/{id}/thumbnail` | JPEG ≤480 px dibuat saat diminta: `draft` → `exif_transpose` → `thumbnail(LANCZOS)`; `ETag` dari sha256 asli; `304` bila `If-None-Match` cocok; tidak menulis file turunan |
| error | id tak dikenal → `404 not_found`; berkas hilang di disk → `410 file_missing`; berkas rusak → `422 image_unreadable`; id dari DB, tidak ada path dari pemanggil |
| `/hasil/:id` | kartu thumbnail `aspect-[4/3]` + `object-fit: cover`, label nama berkas, dimensi, MB, subsampling, tautan “Lihat ukuran penuh” (`target=_blank`), state “memuat pratinjau…” dan “pratinjau tidak tersedia” |
| `/` | thumbnail 40 px per baris daftar bukti (opsional, dikerjakan) |

HEAD didukung karena `FileResponse` versi starlette ini tidak mengirim `Content-Length` pada HEAD;
untuk HEAD gambar dikembalikan `Response` kosong dengan panjang dari `byte_size` di DB.

## Bukti uji (DB `/tmp/tl-img.db`, uploads `/tmp/tl-img-uploads`; DB proyek tidak disentuh)

```
HEAD /image        200 image/jpeg len=106961 cache=private, max-age=3600 etag="f81799…2bba6b"
HEAD /thumbnail    200 image/jpeg len=13204  cache=private, max-age=3600 etag="f81799…2bba6b"
GET  /image        200 106961B image/jpeg (== byte_size di DB)
GET  /thumbnail    200 13204B image/jpeg, dimensi 480×320 (sisi terpanjang 480)
GET  /thumbnail + If-None-Match → 304
sha256 berkas asli sebelum  f8179900dee6b3da60c299dad79784acd6125d17ef9e5cc48a8f59182c8bba6b
sha256 berkas asli sesudah  f8179900dee6b3da60c299dad79784acd6125d17ef9e5cc48a8f59182c8bba6b  (== DB)
id ngawur /image, /thumbnail → 404 {"code":"not_found"}
/../etc/passwd (encoded)    → 404 {"code":"not_found"}
berkas di-rename sementara  → 410 {"code":"file_missing"} ; dikembalikan → 200
isi upload_dir               → tidak ada berkas turunan baru
```

UI (CDP): `/hasil/EVD-CONTOH-A` di 1440 → `naturalWidth > 0`, kotak thumbnail 320 px, `overflowX=0`;
di 390 → kotak 358 px, `overflowX=0`. Daftar `/` → 7 thumbnail, 7 termuat, 38×38 px.
Screenshot `backend/docs/screenshots/{hasil,upload}-{1440,390}.png`.

`npm run build` bersih (index 99.2 kB), `ruff check app scripts` bersih.

Catatan: `backend/data/tracelens.db` tidak disentuh selama tugas ini (uji memakai DB + folder uploads
sementara). Saat pemeriksaan terakhir DB proyek sudah punya tabel `settings` dan 11 baris evidence —
itu berasal dari pemakaian aplikasi oleh proses lain, bukan dari tugas ini.
