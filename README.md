# Trade IDX

Alat bantu keputusan swing trading saham Indonesia (IDX): data harga + berita + fundamental,
dianalisa LLM tiap pagi, dibaca lewat **app HP** (React Native / Expo). Ada jurnal trading real
slicing modal (bagi modal ke saham BELI pakai aturan risiko), dan **Rapor** yang ngukur saran app pakai
harga asli (portofolio uji otomatis + rapor saran BELI).

> Bukan nasihat keuangan. Eksekusi order tetap di broker & keputusan di tangan sendiri.

## Cara kerjanya

```
Server cloud (VPS), Senin-Jumat 05:00 WIB
  scripts/daily.py         harga -> makro -> berita -> sentimen -> sinyal -> paper trading -> brief
  scripts/auto_analisa.py  brief + ISI artikel berita -> LLM (DeepSeek/Gemini/OpenAI) -> data/analysis.json
  backend (FastAPI)        nyajiin analisa, jurnal, berita, slicing ke app (pakai kunci akses)
        |
App HP (APK)              Analisa · Jurnal · Rapor · Berita · Pengaturan
```

## Struktur folder

```
src/                  App HP (TypeScript)
  App.tsx             header + menu bawah + pilih layar
  screens/            satu folder/file per menu: analysis/, journal/, RaporScreen, NewsScreen, SettingsScreen
  components/         potongan UI yang dipakai lintas layar (menu bawah, dropdown, chart, form)
  api.ts              klien server (alamat dicari otomatis, kunci akses)
  analysis.ts         tipe analysis.json + warna aksi (BELI/TUNGGU/HINDARI)
  theme.ts  ui.ts     warna bermakna + style bersama
  format.ts           format angka & tanggal Indonesia
assets/               ikon app + data contoh (tampil sebelum server ketemu)

backend/              Server API (Python / FastAPI)
  api.py              pintu masuk + kunci akses (server jalanin: uvicorn backend.api:app)
  routes/             endpoint per menu app: analysis, journal, rapor, news, settings
trade/                Inti Python: DB, harga, berita, sentimen, sinyal, risiko, jurnal, rapor, LLM, makro
scripts/              Pipeline harian + alat (lihat tabel di bawah)
deploy/               Pasang / update / copot di server Ubuntu

app.json eas.json     konfigurasi Expo & build APK
package.json          dependensi app + perintah (npm run ...)
requirements.txt      dependensi Python
data/                 trade.db, analysis.json, brief (TIDAK ke GitHub)
.env                  API key LLM + kunci akses server (TIDAK ke GitHub)
```

## App HP

```bash
npm install
```

```bash
npm start
```

`npm start` = buka lewat Expo Go (scan QR). `npm run web` = versi browser buat ngetes di laptop.
`npm run typecheck` = cek TypeScript.

Rilis ke HP yang udah terpasang APK (update OTA, gak perlu install ulang):

```bash
npm run ota -- "pesan update"
```

Build APK baru (cuma kalau ganti library native / versi app): `npm run apk`.

App otomatis nyari server: cloud dulu, lalu alamat tersimpan, lalu backend lokal `:8000`.
Kunci akses diisi sekali di menu Pengaturan (disimpan di HP, gak ditanam di kode karena repo publik).

## Backend & pipeline di PC (buat ngembangin)

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn backend.api:app --port 8000
```

Ngetes pakai **salinan** DB biar jurnal asli gak kesentuh: set `TRADE_DATA_DIR` ke folder berisi
salinan `trade.db` (semua script & backend ikut pakai folder itu).

| Script | Kapan | Isinya |
|---|---|---|
| `daily.py` | tiap hari (server) | jalanin 7 langkah di bawah berurutan |
| `backfill_prices.py` | langkah 1 | harga harian (yfinance) |
| `fetch_macro.py` | langkah 2 | IHSG, kurs, emas, minyak, DXY, yield AS, VIX + regime IHSG |
| `fetch_news.py` | langkah 3 | berita Google News per saham |
| `score_news.py` | langkah 4 | skor sentimen (kamus istilah bursa) |
| `generate_signals.py` | langkah 5 | sinyal BUY/HOLD/SELL + pagar fundamental |
| `paper_run.py` | langkah 6 | paper trading (uji maju strategi) |
| `brief.py` | langkah 7 | `data/brief_latest.md`, bahan analisa LLM |
| `auto_analisa.py` | tiap hari (server) | LLM baca brief + isi artikel -> `data/analysis.json` + arsip buat Rapor |
| `fetch_fundamentals.py` | mingguan/bulanan | PER, PBV, ROE, DER, margin |
| `screen.py` | sesekali | pilih ulang saham likuid (`focus_list`) |
| `backtest.py` | riset | uji aturan sinyal/exit ke data historis |

`auto_analisa.py --test` = cek koneksi LLM, `--list-models` = daftar model provider aktif.
Di Claude Code juga ada perintah `/analisa` (Claude yang baca artikel) — hasilnya ke `data/` lokal PC.

## Rapor (ngukur saran app)

Tiap pagi `auto_analisa.py` ngarsip analisanya (tabel `analysis_archive`). Menu Rapor ngitung ulang dari
arsip + harga asli (`trade/rapor.py`), terpisah total dari jurnal asli:
- **Portofolio uji** — modal Rp1,5 juta (`MODAL_UJI`) ngikutin Slicing Modal tiap pagi: beli di Entry (order
  1 hari), jual kalau nyentuh garis jual (rumus sama dengan Jurnal), biaya beli 0,15% & jual 0,25%.
- **Rapor saran** — tiap saran BELI: kebeli? kena Target atau Stop duluan? + rata-rata hasil BELI / TUNGGU /
  HINDARI vs IHSG.
Aturan lengkapnya tampil di app ("Cara ngukurnya"). Butuh ±50 saran (1-2 bulan) buat kesimpulan.

## Server

Pasang sekali (root, Ubuntu): `deploy/setup_server.sh`. Setelah itu server narik kode baru dari
GitHub tiap 15 menit (`deploy/auto_update.sh`) — jadi **push ke `main` = langsung ke server**.
Cek versi yang jalan: `GET /health` -> `version` (commit).

Path yang dipanggil server dan **jangan dipindah/rename** (kalau dipindah, server mati sampai unit
systemd diedit manual sebagai root): `backend/api.py`, `scripts/daily.py`, `scripts/auto_analisa.py`,
`deploy/auto_update.sh`, `deploy/terima_data.sh`, `requirements.txt`. Server pakai Python 3.10.

Isi `.env` (diatur dari menu Pengaturan app, kecuali token):

| Variabel | Isi |
|---|---|
| `TRADE_API_TOKEN` | kunci akses app (wajib di server; kosong = bebas, buat ngetes di PC) |
| `LLM_PROVIDER`, `LLM_MODEL` | otak analisa aktif: `deepseek` / `gemini` / `openai` + nama model |
| `LLM_KEY_<PROVIDER>` | API key per provider, mis. `LLM_KEY_DEEPSEEK` |
