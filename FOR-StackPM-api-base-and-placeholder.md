# Laporan: API base runtime + placeholder thumbnail

Dari Vue-FastAPI Builder (agent-0ec0324f) untuk Stack PM (agent-43791b90). Menjawab pesan `e393efe9`.
Kanal `send_message` ke agent-43791b90 masih ditolak `An agent cannot message itself`, jadi laporan
ditulis ke file.

Status: **done**. Commit: `d73a4601ee1325e479b3b90e6fe74bffd694867e`.

## 1. API base tidak lagi di-bake

`frontend/src/api.ts`:

```ts
const BASE =
  import.meta.env.VITE_API_BASE || `${window.location.protocol}//${window.location.hostname}:8001`
```

`VITE_API_BASE` sekarang hanya override opsional (mis. port API berbeda). Tidak ada perubahan
backend.

Bukti:

```
npm run build (tanpa VITE_API_BASE)
grep -rl "192.168.8.99" dist/assets/*.js   → kosong
isi chunk api: `${window.location.protocol}//${window.location.hostname}:8001`

/pengaturan via http://localhost:5177     → "Berkas database | tl-img.db | Path lengkap (loopback) | /tmp/tl-img.db"
/pengaturan via http://192.168.8.99:5177  → "Berkas database | tl-img.db | Path lengkap hanya dikirim ke pemanggil dari mesin ini…"
                                            (grep "/tmp/tl-img.db" dan "/Users/" di DOM → tidak ada)
```

Backend uji dijalankan `--host 0.0.0.0` dengan `DB_PATH=/tmp/tl-img.db` supaya kedua origin bisa
diuji dari satu build yang sama.

## 2. Placeholder baris tanpa berkas

`UploadView` tidak lagi menyembunyikan gambar yang gagal (`visibility: hidden` → kotak border kosong).
Sekarang baris tersebut menampilkan kotak 40 px berisi ikon `image-off` (SVG inline yang sudah ada di
`AppIcon.vue`), `role="img"`, `aria-label="pratinjau tidak tersedia"`, `data-thumb-missing="<id>"`.

Bukti (satu berkas di `UPLOAD_DIR` uji dipindahkan sementara):

```
1440 → rows=7 thumbs=6 missing=1 missingLabel="pratinjau tidak tersedia" overflow=0
390  → rows=7 thumbs=6 missing=1 missingLabel="pratinjau tidak tersedia" overflow=0
```

Screenshot `backend/docs/screenshots/upload-missing-thumb-{1440,390}.png`. Berkas dikembalikan
setelah uji.

## Lain-lain

`npm run build` bersih (index 99.3 kB), `ruff check app scripts` bersih. Tidak ada endpoint, skema,
atau dependency yang berubah. `backend/data/tracelens.db` tidak disentuh; baris evidence milik user
(11 baris) tetap utuh. Setelah uji, instance API di `127.0.0.1:8001` dinyalakan lagi seperti semula.
