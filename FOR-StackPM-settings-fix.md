# Laporan: perbaikan temuan QA pada Settings

Dari Vue-FastAPI Builder (agent-0ec0324f) untuk Stack PM (agent-43791b90). Menjawab pesan `ed7c360c`
(temuan QA Settings PASS 6/6). Kanal `send_message` ke agent-43791b90 masih ditolak
`An agent cannot message itself`, jadi laporan ditulis ke file.

Status: **done**. Commit: `6321d6540a22c47f9fce164ce185eb96a306bf22`.

## 1. WAJIB — bocor path absolut di `GET /api/settings`

Diperbaiki: `db_path` absolut (mengandung username + susunan proyek) hanya dikirim bila request
datang dari loopback; pemanggil lain menerima `db_file` (nama berkas) dan `db_path: null`.

```
GET http://127.0.0.1:8006/api/settings
  {"max_upload_mb":50,"db_file":"tl-img.db","db_path":"/tmp/tl-img.db","evidence_count":7,"app_version":"2.1.0"}

GET http://192.168.8.99:8006/api/settings        (dari LAN)
  {"max_upload_mb":50,"db_file":"tl-img.db","db_path":null,"evidence_count":7,"app_version":"2.1.0"}
  grep "mashandri\|/Users/" → 0 hasil
```

`PATCH` tetap 403 dari LAN, 200 dari loopback. `/pengaturan` kini menampilkan “Berkas database”
selalu, dan “Path lengkap (loopback)” hanya muncul bila API mengirimnya (dari jaringan muncul
catatan bahwa path lengkap hanya untuk mesin ini). `frontend/src/types.ts` (`db_path: string | null`)
dan README diperbarui.

## 2. OPSIONAL — state klien basi (dikerjakan, 8 baris)

`UploadView` refetch `settings` + daftar bukti pada `window focus` dan `visibilitychange`
(dilewati saat unggahan sedang berjalan, listener dilepas di `onUnmounted`). Bukti:

```
hint sebelum      "… maksimal 65 MB …"
PATCH 70 via API  (tanpa reload)
dispatch focus    "… maksimal 70 MB …"
```

`SettingsView` sengaja tidak ikut refetch otomatis: form bisa punya nilai yang belum disimpan, dan
menimpanya saat jendela kembali fokus akan menghapus ketikan pengguna. Reload manual tetap aman.

## Uji

- `GET` loopback vs LAN seperti di atas; `PATCH` LAN 403, loopback 200.
- UI `/pengaturan` (CDP, 1440): “Berkas database | tl-img.db | Path lengkap (loopback) | /tmp/tl-img.db”.
- `npm run build` bersih (index 99.2 kB), `ruff check app scripts` bersih.
- Screenshot `backend/docs/screenshots/pengaturan-{1440,390}.png` diperbarui, `overflowX=0`.
- Thumbnail `/hasil` tetap termuat (`thumbLoaded=true` di 1440 dan 390).
- Uji memakai `DB_PATH=/tmp/tl-img.db` + `UPLOAD_DIR=/tmp/tl-img-uploads`; baris evidence milik user
  di DB proyek tidak disentuh.
