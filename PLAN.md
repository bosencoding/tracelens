# TraceLens — Iteration 1 Plan v2 (goal changed by user)
v1 (PRNU scope) superseded: PRNU needs CFA/PRNU estimation across many images — overkill for a coursework deliverable. New goal: **identify a JPEG's camera/encoder signature** from what a single JPEG actually carries.
Folder name still `PRNU-TraceLens/` (legacy path, keep it — builder references it).

## Product
Upload one JPEG → read its signature → say which camera/encoder most likely produced it → export a short report. Indonesian UI. Data sintetis, diberi label.

## What "signature" means here (honest scope)
1. **EXIF identity**: Make, Model, LensModel, Software, DateTimeOriginal, SerialNumber, offset/thumbnail mismatch.
2. **JPEG quantization tables**: the 2 tables (luma/chroma) per quality — a 128-value fingerprint. Cosine similarity vs reference table set.
3. **Encoder fingerprint**: libjpeg vs libjpeg-turbo vs Adobe vs Apple ordering, subsampling (4:4:4 / 4:2:0 / 4:2:2), restart interval, Huffman table variant.
4. **Edit trace**: thumbnail vs main mismatch, double compression (table pair not from one encoder), Software tag after capture date, missing MakerNote.
Verdict = weighted vote with confidence + explicit "tidak dapat dipastikan" band. **No PRNU, no wavelet, no PCE, no hot-pixel claims.**

Limitation shown in UI: quantization tables identify encoder/processing pipeline reliably; camera model only when it matches the reference set; EXIF alone is spoofable.

## Stack (fixed by user)
Vue 3 + TS + Vite + Tailwind 3 | FastAPI + Pydantic v2 (Python 3.11, uv) + Pillow | **SQLite** — file tunggal `data/tracelens.db`, stdlib `sqlite3` + `sqlite3` schema in `sql/`. No Supabase, no keys, no RLS, no network DB.

## Routes (3, cut from 4)
| route | isi |
|---|---|
| `/` | drop zone + daftar bukti tersimpan (id, nama file, verdict, confidence) |
| `/hasil/:id` | verdict card + tab: EXIF · Tabel Kuantisasi · Jejak Edit · Ringkasan |
| `/laporan/:id` | dokumen ringkas siap cetak (CSS `@media print`, simpan PDF via dialog browser) |
| `/pengaturan` | pengaturan runtime: batas unggahan (MB), info baca-saja (DB, jumlah bukti, versi) |

Cut: `/bulk`, `/analysis` tab ELA/DCT/Hex, seal ECDSA, PDF server-side, auth.

## Tasks (Vue-FastAPI Builder owns all)
T1 token + shell: Tailwind theme dari DESIGN.md frontmatter — primary `#004E9F`, surface `#F8F9FF`, on-surface `#0B1C30`, outline `#C1C6D5`, outline-variant, success `#16A34A`, tamper `#DC2626`, advisory `#F59E0B`, container `#EFF4FF/#E5EEFF/#DCE9FF`, secondary `#006C49`, error `#BA1A1A`. Inter UI; `label-md` = JetBrains Mono 12/16/500 tabular untuk hash, serial, timestamp. Radius kartu 16, hero 24, skala 8pt. Header: TraceLens, `#CAS-…`, mode badge, nav. Tanpa gradien; glass hanya di HUD.
T2 `/` upload: terima `.jpg/.jpeg` maks 50 MB (`MAX_UPLOAD_MB`), tolak selain itu dengan pesan jelas; daftar riwayat dari API; setelah unggah → `/hasil/:id`.
T3 `/hasil/:id`: verdict card (kamera/encoder paling mungkin + confidence bar + catatan batasan), 4 tab: EXIF (field + tandai hilang/tidak konsisten), Tabel Kuantisasi (2 grid 8×8 angka mono + fingerprint hex), Jejak Edit (thumbnail mismatch, double compression, software-after-capture), Ringkasan (skor per komponen + alasan).
T4b `/pengaturan`: form batas unggahan (number, 1–500 MB) + tombol Simpan, status sukses/gagal, info baca-saja (path DB, jumlah evidence, versi app). Nilai disimpan di tabel `settings` (key/value) supaya tahan restart; `MAX_UPLOAD_MB` dari env hanya nilai awal. `UploadView` mengambil batas dari `GET /api/settings`, bukan konstanta. API: `GET /api/settings`, `PATCH /api/settings` (validasi 1–500, 422 dengan nama field). Tanpa auth — sebutkan di README bahwa siapa pun di jaringan bisa mengubahnya.
T4 `/laporan/:id`: header dokumen, identitas file, verdict, ringkasan temuan, disclaimer sintetis + batasan metode, tombol Cetak/Simpan PDF lewat print CSS.
T5 FastAPI: `POST /api/evidence` (multipart, validasi mime+ukuran), `GET /api/evidence`, `GET /api/evidence/{id}`, `GET /api/evidence/{id}/signature` (EXIF, qtable pair, fingerprint hex, encoder guess, subsampling), `GET /api/evidence/{id}/matches` (top-3 + similarity), `DELETE /api/evidence/{id}`. Pydantic sebagai kontrak; error `{detail, code}`; 404/415/422.
T6 hitung di server: qtable cosine similarity vs tabel referensi; fingerprint hex = sha256 dari 128 nilai qtable ternormalisasi; confidence = gabungan (EXIF model + similarity + encoder match), tiap komponen ditampilkan. Tidak ada angka hardcoded di klien.
T7 data: tabel `evidence`, `signatures`, `matches`, `reference_cameras`. Seed idempoten: 5–8 JPEG sintetis buatan sendiri (gambar sama di-encode Pillow quality 75/92, subsampling 4:2:0/4:4:4, EXIF dihapus, EXIF palsu) + 3 "kamera referensi" yang dilabeli contoh. Jangan klaim data kamera nyata.

## Acceptance (QA)
A1 3 route + `/` render; tanpa scroll horizontal @1440 dan @390; id tak dikenal → halaman error jelas, bukan blank.
A2 token sesuai DESIGN.md frontmatter (primary/surface/on-surface/outline, status colors), Inter body, JetBrains Mono tabular pada hash/serial, radius 16/24.
A3 unggah JPEG valid → `/hasil/:id` tampil verdict + confidence; unggah `.png`/`.txt`/21 MB → pesan error jelas, tanpa stack trace.
A4 tab EXIF/kuantisasi/jejak/ringkasan menampilkan data berbeda; angka qtable dari `GET /signature`, bukan literal JS (ubah seed → UI ikut).
A5 `/matches` memberi 3 kandidat similarity menurun, konsisten dengan tabel referensi.
A6 `/laporan/:id`: print CSS rapi (nav/tombol hilang saat print), disclaimer + batasan metode tercetak.
A7 API: 404 id tak dikenal, 415 mime salah, 422 body salah (nama field), CORS `http://localhost:5173`, tanpa traceback, id milik studi lain tidak membocorkan baris.
A8 tidak ada `service_role`/JWT di `dist/`, localStorage, atau request browser; `.env` tidak ikut build.

## Loop
builder deliver → PM kirim paket (path, run cmds, port, curl, id contoh) → QA verdict per item → mismatch balik ke builder dengan evaluasi QA saja → ulang sampai A1–A8 lulus.
