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
| A8 | tanpa rahasia + DB lokal | `grep -ri "service_role\|SUPABASE\|api_key" dist/` + devtools network + localStorage; `ls data/*.db` | tidak ada key/token di bundle, storage, atau request browser; DB = satu file SQLite lokal, tidak ada panggilan DB keluar |

Tidak diuji di v2 (dipotong dari goal): `/bulk`, klaster, tab ELA/DCT/Hex, PCE/SNR/PRNU, seal ECDSA, PDF server-side, auth.
FAIL wajib menyertakan: item, langkah repro, hasil vs harapan, screenshot, satu dugaan penyebab. Tidak memperbaiki kode.
