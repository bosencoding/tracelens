# TraceLens — QA Checklist (iterasi 1, v2: signature JPEG, bukan PRNU)
Target: `http://localhost:5173` (Vue) + `http://localhost:8001` (FastAPI). Data sintetis, dilabeli. Tanpa auth.
Acuan: `/Users/mashandri/OpenBot/Shared/PRNU-TraceLens/PLAN.md` (v2). Owner uji: QA Tester.

| # | item | cara uji | PASS |
|---|---|---|---|
| A1 | 3 route hidup | `/`, `/hasil/:id`, `/laporan/:id`; id tak dikenal | semua render tanpa error console fatal; tanpa scroll horizontal @1440 & @390; id ngawur → halaman error jelas, bukan blank |
| A2 | token sesuai | `getComputedStyle` pada tombol primary, kartu, nilai hash | primary `rgb(0,78,159)`, surface `rgb(248,249,255)`, on-surface `rgb(11,28,48)`, Inter body, JetBrains Mono tabular pada hash/serial, radius kartu 16 / hero 24 |
| A3 | unggah | unggah JPEG valid; lalu `.png`, `.txt`, JPEG 51 MB | valid → pindah `/hasil/:id` dengan verdict + confidence; 3 kasus invalid → pesan jelas menyebut 50 MB, tanpa stack trace; JPEG 21 MB harus DITERIMA (201) |
| A4 | tab hasil | klik EXIF / Tabel Kuantisasi / Jejak Edit / Ringkasan | tiap tab data berbeda; 128 nilai qtable + fingerprint hex sama dengan `GET /api/evidence/{id}/signature`; ubah 1 baris seed → UI ikut berubah |
| A5 | kandidat | bandingkan dengan `GET /api/evidence/{id}/matches` | tepat 3 kandidat, similarity menurun, jumlah = isi tabel `reference_cameras` |
| A6 | laporan | `/laporan/:id`, print preview | nav/tombol hilang saat print, disclaimer "data sintetis" + batasan metode tercetak, tata letak tidak terpotong |
| A7 | API | curl: id tak dikenal, mime salah, body salah, OPTIONS, id studi lain | 404 `{detail, code}`; 415 mime salah; 413 untuk >50 MB; 422 dengan nama field; CORS `access-control-allow-origin: http://localhost:5173`; tanpa traceback; id studi lain → 404/403 tanpa bocor baris |
| S1 | halaman settings | buka `/pengaturan` | form tampil, token sesuai (A2), nilai awal = batas aktif |
| S2 | simpan nilai | PATCH 100 lalu GET | `GET /api/settings` = 100; reload halaman tetap 100 |
| S3 | efek ke unggahan | set 100 → unggah 60 MB; set 10 → unggah 60 MB | 201 saat batas 100; 413 `file_too_large` saat batas 10 |
| S4 | validasi | PATCH 0, -5, "abc", 501 | 422 dengan nama field, nilai lama tidak berubah |
| S5 | tahan restart | restart backend, GET settings | nilai terakhir masih berlaku |
| S6 | klien ikut API | set batas 5 MB, pilih file 8 MB | ditolak di klien dengan angka dari API (bukan hardcode) |
| B1 | thumbnail tampil | buka `/hasil/:id` | foto tampil dengan rasio tetap (tidak ada layout shift), label nama file + dimensi + ukuran, tautan "Lihat ukuran penuh" membuka `/api/evidence/{id}/image` |
| B2 | endpoint gambar | `curl -I /api/evidence/{id}/image` dan `/thumbnail` | 200 `image/jpeg`, content-length masuk akal, `Cache-Control` di thumbnail; id ngawur → 404 `{detail, code}` |
| B3 | bukti tidak diubah | bandingkan `sha256` file di `upload_dir` dengan kolom `sha256` DB, sebelum dan sesudah memanggil `/thumbnail` | identik; tidak ada file asli yang ditimpa, tidak ada re-encode |
| B4 | gagal dengan rapi | hapus sementara file di disk (uji di DB `/tmp`, bukan proyek) | halaman hasil tetap render, pratinjau menampilkan pesan "tidak tersedia", bukan blank/500 |
| A8 | tanpa rahasia + DB lokal | `grep -ri "service_role\|SUPABASE\|api_key" dist/` + devtools network + localStorage; `ls data/*.db` | tidak ada key/token di bundle, storage, atau request browser; DB = satu file SQLite lokal, tidak ada panggilan DB keluar |

Tidak diuji di v2 (dipotong dari goal): `/bulk`, klaster, tab ELA/DCT/Hex, PCE/SNR/PRNU, seal ECDSA, PDF server-side, auth.
FAIL wajib menyertakan: item, langkah repro, hasil vs harapan, screenshot, satu dugaan penyebab. Tidak memperbaiki kode.
