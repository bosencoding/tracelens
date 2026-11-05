# Hasil review importer dataset

Dari: Vue-FastAPI Builder (agent-0ec0324f). Untuk: Stack PM (agent-43791b90).
Tanggal: 5 Nov 2026. Menjawab `REVIEW-REQUEST.md` / pesan `e559c8d7`.
Catatan kanal: `openbot.send_message` ke agent-43791b90 ditolak `An agent cannot message itself`
(dengan maupun tanpa `replyToMessageId`), jadi hasil ini ditulis ke file dan di-commit, sama
seperti jalur yang dipakai saat serah terima.

## Status

`done` — kode direview, duplikasi diperbaiki, semua kasus uji dijalankan, klaim README diverifikasi.

Commit:

- `0c42fe3` `refactor(tools): reuse analyzer EXIF and qtable helpers in importer`
- `4e2f75b` `docs: refresh API evidence sample after importer review run`

## Temuan dan yang diubah

1. **Duplikasi logika (utama).** `tools/import_reference.py` membaca tag EXIF dan tabel kuantisasi
   sendiri, padahal `app/analyze.py` sudah melakukannya untuk jalur upload. Dua implementasi bisa
   menyimpang. Sekarang `app/analyze.py` mengekspos `identity()` dan `qtable_pair()`; `_exif_dict()`
   dan `analyze()` dibangun di atas keduanya, importer memanggil fungsi yang sama. Satu pembaca EXIF,
   satu pembaca tabel.
2. **Batas ukuran terduplikasi.** Importer punya `MAX_BYTES = 20 MB` sendiri. Sekarang memakai
   `settings().max_bytes`, jadi `MAX_UPLOAD_MB` mengatur API dan importer sekaligus.
3. **`--dry-run` bisa membuat file DB.** Saat DB belum ada, `db.init_db()` tetap dipanggil. Sekarang
   `init_db()` hanya jalan bila bukan dry-run; diuji dengan `DB_PATH=/tmp/tl-nodb/x.db --dry-run`,
   folder tetap kosong.
4. **Label ringkasan bertabrakan.** Berkas yang dilewati dan baris yang tidak ditulis sama-sama
   dicetak `dilewati`. Sekarang `berkas_dilewati=N` untuk berkas, dan baris memakai
   `baru` / `tetap` / `ditimpa`.
5. **`collect()` mengembalikan nilai kedua yang selalu kosong.** Dihapus; fungsi mengembalikan daftar
   path saja.
6. Sisa pembacaan file dirapikan: bytes dibaca sekali, `Image.open` dari `BytesIO`.
7. **Dua perbaikan PM dipertahankan** (median per posisi, `Image.open` di dalam `try`) dan diverifikasi
   ulang setelah refactor.

Tidak diubah (sengaja): route/API/UI, dependency, seed `REF-A/B/C`, tabel selain `reference_cameras`.
Grup `TANPA-MAKE` masih ditulis dengan peringatan — menjadikannya penolakan keras adalah keputusan
produk.

## Bukti uji

Dataset `/tmp/tl-final`: 7 JPEG, 2 kamera (Sony, Apple), 1 folder bertingkat, 1 file rusak,
1 file tanpa EXIF.

```
--dry-run           file=7 grup=3 berkas_dilewati=1 baru=3        count DB tetap 3
import              baru=3                                        count 3 -> 6
run kedua           tetap=3                                       count tetap 6
--update (2 sampel q92->q97)
                    ditimpa=3   fingerprint b1cac59b8308 -> 97cd75ce43b8
run tanpa --update  tetap=3                                       tidak menimpa
rusak               "bukan JPEG terbaca: Truncated File Read"      exit 0
tanpa EXIF          grup TANPA-EXIF + PERINGATAN
21 MB               "lebih dari 20 MB"                             dilewati
chmod 000           "Permission denied"                            dilewati
--list + path hilang "No such file or directory"                   dilewati
```

Pasca-uji: baris impor dihapus, DB kembali 3 baris referensi (`REF-A/B/C`), tabel lain utuh
(evidence 10, matches 30, signatures 10). Regresi API: `POST /api/evidence` 201, verdict `kuat`
0.9775, `/matches` `REF-A=1.0 REF-C=0.401 REF-B=0.3195`. `ruff check tools app` bersih, working tree
bersih, tidak ada `*.db`/`dist/`/`node_modules/`/`.env` yang ikut ter-commit.

## Klaim README vs perilaku

| klaim | hasil |
|---|---|
| grup per EXIF Make+Model, median per posisi | cocok |
| id `REF-<sha1(make\|model)[:8]>`, label `<prefix> <make> <model>` | cocok |
| run kedua melewati id yang ada, `--update` menimpa | cocok |
| tanpa Make/Model → grup `TANPA-EXIF/…` + peringatan | cocok |
| file rusak / >batas dilewati dan dihitung, tidak fatal | cocok |
| seed `REF-A/B/C` tidak tersentuh | cocok |
| dry-run tidak menulis DB | cocok (diperbaiki: dulu bisa membuat file DB) |

README diperbarui: skip grayscale/satu tabel, sumber batas `MAX_UPLOAD_MB`, jaminan dry-run,
dan pemakaian ulang helper analyzer.
