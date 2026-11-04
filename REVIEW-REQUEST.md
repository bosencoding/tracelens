# Serah terima: review importer dataset (dari Stack PM)

Tanggal: 4 Nov 2026. Repo: `/Users/mashandri/OpenBot/Shared/PRNU-TraceLens`, branch `main`.
Commit yang direview: `c5a3686` (di atas `ed9ea63`).

## Kenapa ini ada

Kanal `openbot.send_message` mati di sesi PM (server MCP `openbot` tidak terhubung), jadi tugas ini
tidak bisa dikirim lewat pesan. PM menulis importer sendiri agar pekerjaan tidak berhenti; sekarang
diserahkan ke builder untuk direview dan diperbaiki bila perlu. Kamu pemilik kode sesudah ini.

## Yang ditambahkan

| file | isi |
|---|---|
| `backend/tools/import_reference.py` | importer folder/list JPEG → baris `reference_cameras` |
| `backend/tools/__init__.py` | kosong (agar `python -m tools.import_reference` jalan) |
| `README.md` | bagian "Real datasets (importer)" |

Perilaku:
- Sumber: `--dir <folder>` (rekursif, `.jpg/.jpeg`) atau `--list <file>` (path per baris).
- Grup per EXIF `Make` + `Model`. Tabel kuantisasi representatif = **median per posisi** (64 nilai luma + 64 chroma), subsampling & encoder = modus.
- Id baris = `REF-<sha1(make|model)[:8]>`; label `<prefix> <make> <model>`.
- Idempoten: run kedua "dilewati"; `--update` menimpa. `--dry-run` tidak menulis DB.
- File tanpa Make/Model → grup `TANPA-EXIF/...` + peringatan. File rusak atau >20 MB → dilewati dan dihitung, tidak fatal.
- Tidak menambah dependency (Pillow + stdlib + modul `app.*` yang sudah ada).

## Bukti yang sudah dijalankan PM

```
uv run ruff format tools/import_reference.py && uv run ruff check tools/import_reference.py  # All checks passed
uv run python -m tools.import_reference --dir /tmp/ds2 --dry-run    # file=4 grup=2 baru=2, count DB tetap 3
uv run python -m tools.import_reference --dir /tmp/ds-test ...      # 7 file, 1 rusak → "dilewati=1", crash tidak
run kedua                                                           # semua "dilewati", count tetap
sqlite3 data/tracelens.db "select count(*) from reference_cameras"   # seed REF-A/B/C utuh
```

Dua bug yang PM temukan dan perbaiki sebelum commit (jangan dikembalikan):
1. Median awalnya dihitung atas gabungan 64×n nilai → tabel jadi 1 nilai, semua grup dapat fingerprint identik. Sekarang `median_table()` median per posisi.
2. `Image.open` di luar `try` → JPEG rusak melempar `UnidentifiedImageError`. Sekarang ditangkap, jadi baris skip.

Baris uji PM (`REF-03D1E76B`, `REF-21A1BAC9`) sudah dihapus dari DB; DB kembali 3 baris. `/tmp/ds-test`, `/tmp/ds2` sudah dihapus.

## Yang diminta darimu

1. Review kode `c5a3686`: baca `app/jpeg.py`, `app/analyze.py`, `app/db.py` dulu — importer harus memakai ulang, bukan menduplikasi logika.
2. Uji sendiri di folder nyata (boleh dataset asli bila sudah ada, atau buat 6+ JPEG dua model di `/tmp`): `--dry-run`, import, run kedua, `--update`, satu file rusak, satu file tanpa EXIF.
3. Verifikasi klaim di README cocok dengan perilaku; perbaiki kalau tidak.
4. Perbaiki yang salah, commit conventional commit, lapor: temuan, hash commit, output perintah uji.

## Batasan

- Jangan menambah dependency baru, jangan ubah route/API/UI, jangan sentuh baris seed `REF-A/B/C` tanpa `--update`.
- Jangan commit dataset, `*.db`, `node_modules`, `dist`, `.env`.
- Jangan deploy ke publik, jangan mengubah repo/agen lain.
- Catatan domain: hanya JPEG native kamera yang membawa tabel kamera; konversi RAW→JPEG menghasilkan tabel libjpeg, jadi tidak sah untuk referensi.

## Kalimat untuk user tempel di chat builder

> Baca `/Users/mashandri/OpenBot/Shared/PRNU-TraceLens/REVIEW-REQUEST.md`, kerjakan bagian "Yang diminta darimu": review commit `c5a3686` (importer `backend/tools/import_reference.py`), uji sendiri, perbaiki bila ada yang salah, commit, lalu lapor temuan + hash commit + output uji.
