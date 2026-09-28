# Catatan buat agen (Claude Code)

Peta folder & cara jalanin: lihat README.md. Pengguna dipanggil "Bapak", bahasa Indonesia santai.

## Jangan dilanggar
- Server produksi jalanin path tetap: `backend/api.py` (`uvicorn backend.api:app`), `scripts/daily.py`,
  `scripts/auto_analisa.py`, `deploy/auto_update.sh`, `deploy/terima_data.sh`, `requirements.txt`.
  Push ke `main` = auto-deploy ke server dalam <=15 menit. Jangan pindah/rename path itu.
- Jadwal tanpa root: backend/scheduler.py (thread di backend, aktif cuma kalau TRADE_API_TOKEN diisi) jalanin
  update harga sore 17.00 WIB. Timer systemd (05:00) cuma bisa diubah root lewat Workbench.
- Server = Python 3.10: jangan pakai sintaks 3.11+ (f-string bersarang/backslash di f-string, `except*`, dll).
- Ngetes backend/pipeline/jurnal: SELALU pakai salinan DB (`TRADE_DATA_DIR=<folder salinan>`).
  Jangan pernah isi jurnal asli (`data/trade.db`) dengan data tes.
- `.env` di root dibaca juga oleh Expo: JANGAN bikin variabel `EXPO_PUBLIC_*` berisi rahasia (ikut ke bundle
  app, dan bundle OTA bisa diunduh publik). Kunci akses app diisi manual di Pengaturan, jangan ditanam di kode.
- UI & chat: tanpa emoji (pakai Ionicons). Bahasa awam tanpa singkatan (Target/Entry/Stop, bukan T/E/S).
  Angka rusak (NaN, "Rp–") jangan sampai tampil; data belum ada = disembunyiin. Warna dari `src/theme.ts`.

## Rilis
Backend berubah: push -> tunggu `GET /health` nunjukin commit baru -> baru `npm run ota -- "pesan"`
(app baru jangan nongol duluan sebelum server punya endpoint/field-nya).

## Expo
Expo SDK 57 — baca dokumen versi persisnya di https://docs.expo.dev/versions/v57.0.0/ sebelum nulis kode app.
