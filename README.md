# Trade — Analisis Saham IDX (Harga + Berita + Fundamental)

Alat bantu keputusan **beli/jual saham** (swing trading, harian–mingguan) berbasis
**teknikal + sentimen berita + fundamental**, dengan **keputusan akhir dirangkum Claude (LLM)**.
**Fokus: saham Indonesia (IDX)** — backtest 5 tahun nunjukin IDX punya edge, US enggak.
Kode tetap market-agnostic (atur di [`trade/config.py`](trade/config.py) → `MARKETS`).

> ⚠️ **Bukan nasihat keuangan.** Sistem ini alat bantu keputusan, bukan mesin ATM.
> Jalur wajib sebelum pakai duit beneran: **backtest → paper trading → duit kecil.**

## Status: Fase 0–5 ✅ + Dashboard + Brief — operasional

| Fase | Isi | Status |
|------|-----|--------|
| 0 | Data pipeline: harga (yfinance) + berita (Google News RSS) → SQLite | ✅ |
| 1 | Sentiment engine (skor berita −1..+1) | ✅ |
| 2 | Signal engine (teknikal + sentimen → BUY/HOLD/SELL) + pagar fundamental | ✅ |
| 3 | Backtest engine (point-in-time, anti-lookahead, trailing stop + biaya) | ✅ |
| 4 | Paper trading (portfolio FULL vs TECH + benchmark, A/B sentimen) | ✅ |
| — | Dashboard Streamlit + Keputusan Claude (`analysis.json`) + brief harian | ✅ |
| 5 | Jurnal trading real (duit kecil): catat entry/exit, P/L, evaluasi vs sinyal | ✅ tooling |
| + | `/analisa` diperluas: top-20 kandidat + **lensa big cap/LQ45** + penanda **musim MSCI** (`trade/msci.py`) | ✅ |
| + | Jurnal dashboard: garis **Target Cuan** (checkpoint) + **horizon lama-tahan** (dari backtest) | ✅ |
| + | `scripts/auto_analisa.py`: pipeline `/analisa` OTOMATIS (Gemini free + Tavily baca artikel) — otak buat app | 🧪 eksperimental |
| + | App mobile (Expo/React Native) di `mobile/` — rangka, render `analysis.json` + bottom-nav | 🚧 WIP |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

## Alur harian (3 langkah)

```bash
# 1. Refresh SEMUA data + sinyal + brief + paper trading (sekali gas)
python scripts/daily.py           # otomatis juga bikin data/brief_latest.md

# 2. Di Claude Code, ketik:  /analisa
#    -> Claude baca brief + BACA ARTIKEL BERITA ASLI (web) tiap kandidat
#       (cross-check clickbait judul) -> tulis keputusan ke data/analysis.json

# 3. Lihat dashboard
streamlit run dashboard.py        # -> http://localhost:8501
```

**Nggak pakai scheduler — `/analisa` yang jamin data fresh:** tiap kamu ketik `/analisa`, Claude
ngecek tanggal data dulu; kalau basi (lebih tua dari hari bursa terakhir) dia **otomatis narik
data baru** (`scripts/daily.py`) sebelum mutusin. Jadi satu perintah = data fresh + keputusan —
tanpa task yang bisa mati di tengah jalan atau laptop kebangun sendiri jam 8 pagi. (Masih bisa
`python scripts/daily.py` manual kapan aja kalau mau.)

## Ritme operasional (cheatsheet)

Sistem udah kelar (Fase 0–5). Sekarang tinggal **dipakai** — low-maintenance.

**Tiap pagi hari bursa:**
- [ ] Buka Claude Code → ketik **`/analisa`** — kalau data basi, Claude **auto-refresh** dulu (`daily.py`), baru baca artikel asli & update keputusan. Nggak usah tarik data manual.
- [ ] `streamlit run dashboard.py` → lihat **Keputusan Claude**
- [ ] Kalau trading: eksekusi di **broker sendiri**, lalu catat di tab **Jurnal**

**Mingguan:**
- [ ] `python scripts/fetch_fundamentals.py` (fundamental berubah pelan)
- [ ] Sesekali `python scripts/screen.py` (refresh saham likuid → `focus_list`)

**Fase sekarang: BUKTIKAN dulu.** Jalur wajib: backtest → paper → **duit kecil + jurnal** → baru
scale modal. Biarin paper trading + jurnal jalan berminggu-minggu, pantau: win rate naik?
disiplin stop? keputusan mana yang cuan? **Kumpulin bukti SEBELUM nambah modal.**

> ⚠️ Bukan nasihat keuangan. Eksekusi & keputusan di tangan kamu; alat ini bantu analisa + catat.

## Jurnal trading (Fase 5)

Catat trade **REAL** (duit kecil) buat evaluasi disiplin — **bukan nasihat / eksekusi order**.
P/L pakai model biaya IDX yang sama dengan paper/backtest. 1 lot = 100 lembar.

```bash
# catat posisi baru
python scripts/journal.py add CMRY --price 4690 --lot 2 --stop 4480 --note "ikut /analisa"
# tutup posisi (id dari report)
python scripts/journal.py close 1 --price 4900
# laporan P/L + trailing stop + bandingin sama sinyal sistem
python scripts/journal.py
# kalkulator ukuran posisi (risk-based): berapa lot biar risiko terkontrol
python scripts/journal.py size --capital 1500000 --entry 4690 --stop 4480 --risk 2
```

Muncul juga di tab **Jurnal** dashboard: posisi terbuka + P/L + **trailing stop** (di mana
keluar, biar konsisten sama backtest) + sinyal sistem + kalkulator **sizing** (berapa lot).
Data jurnal **privat** (di `data/trade.db`, gitignored).

> **Kenapa trailing & sizing penting:** backtest nunjukin exit *trailing* jauh ngalahin *target fixed*
> (avg winner 20% vs 14% — motong pemenang = buang edge). Dan sizing risk-based bikin tiap kekalahan
> ~sama & terkontrol. Entry cuma ~20% dari hasil; **risk & exit ~80%.**

## Otak dashboard: `data/analysis.json`

Dashboard menaruh **Keputusan Claude di depan**, sinyal mesin cuma pembanding.
`analysis.json` diisi lewat `/analisa`: Claude baca `brief_latest.md` **plus artikel
berita aslinya** (via web, cross-check clickbait judul) — bukan cuma judul. Formatnya:

```json
{
  "generated": "2026-08-30",
  "macro": "IHSG ... USD/IDR ... tema sektor ...",
  "calls": [
    {"ticker": "BBNI.JK", "action": "BELI", "conviction": "Tinggi", "flag": "good",
     "entry": 3710, "target": 4050, "stop": 3480, "reason": "..."}
  ]
}
```
`action`: BELI / BELI (tenang) / BELI (spekulatif) / TUNGGU PULLBACK / HINDARI · `flag`: good / neutral / caution / danger.
Ada juga field `positions` (review posisi jurnal: **TAHAN / WASPADA / JUAL**), dan `modal`+`lot` per call
kalau dijalankan `/analisa modal <angka>` (sizing otomatis). `/analisa` selalu ikut nilai **big cap/LQ45**
(lensa turnover, walau skor mesin HOLD) dan nyelipin peringatan kalau lagi **musim rebalancing MSCI**.

## App mobile + pipeline otomatis (WIP)

Biar nggak perlu buka Claude Code tiap hari, ada dua bagian baru (masih eksperimental):

- **`scripts/auto_analisa.py`** — versi KODE dari `/analisa`: kumpulin data + **baca isi berita**
  (via [Tavily](https://tavily.com), search API gratis) → **Gemini (free tier)** mutusin
  BELI/HINDARI + alasan (skeptis clickbait) → tulis `data/analysis.json`. Otak gratis pengganti
  Claude Code buat backend/otomatis. Key dibaca dari `.env` (**gitignored**): `GEMINI_API_KEY`,
  `TAVILY_API_KEY`.
  ```bash
  .venv/Scripts/python.exe scripts/auto_analisa.py --list-models    # cek model yang bisa dipakai
  .venv/Scripts/python.exe scripts/auto_analisa.py --modal 100jt     # analisa + sizing lot
  ```
- **`mobile/`** — app mobile (Expo + React Native + TypeScript) yang render `analysis.json` jadi
  kartu BELI/TUNGGU/HINDARI + review posisi, dengan **bottom-nav** ala app. Masih rangka (data
  sampel bundel), belum nyambung backend.
  ```bash
  cd mobile && npx expo start --tunnel     # scan QR pakai Expo Go (--tunnel: nembus WiFi kantor)
  ```

## Atur saham yang dipantau

Screener likuiditas ([`scripts/screen.py`](scripts/screen.py)) milih otomatis `focus_list`
dari seluruh universe IDX. Untuk paksa/tambah manual, edit
[`config/watchlist.yaml`](config/watchlist.yaml) (IDX pakai suffix `.JK`, mis. `BBCA.JK`).

## Struktur

```
trade/            package inti (market-agnostic)
  config.py       path + watchlist + MARKETS
  db.py           SQLite: skema + simpan
  prices.py       tarik harga (yfinance)
  news.py         tarik berita (Google News RSS)
  sentiment.py    skor sentimen berita
  fundamentals.py rasio + bendera merah (pagar anti-sampah)
  macro.py        regime IHSG (vs MA200) + indikator makro (kurs/komoditas/global)
  msci.py         penanda musim rebalancing MSCI (arus asing big cap = flow, bukan tesis)
  risk.py         sizing (risk-based) + trailing stop (exit disiplin, samain backtest)
  indicators.py   MA / RSI / ATR
  signals.py      signal engine (teknikal + sentimen)
  backtest.py     backtest point-in-time (trailing + biaya)
  paper.py        simulasi portfolio paper
  journal.py      jurnal trading real (Fase 5): P/L + evaluasi vs sinyal
  screener.py     screener likuiditas -> focus_list
  universe.py     ambil daftar saham IDX resmi
scripts/          entry point (daily.py orkestrator, auto_analisa.py = /analisa via Gemini, dll.)
config/           watchlist.yaml
data/             trade.db, analysis.json, brief_*.md, *.csv  (di-gitignore)
dashboard.py      Streamlit (Beranda/Sinyal/Jurnal + Target Cuan & horizon di posisi)
mobile/           app mobile Expo/React Native (rangka) — .env & node_modules gitignored
```

## Jalanin per-bagian (kalau perlu)

```bash
python scripts/init_db.py            # bikin DB + skema
python scripts/load_universe.py      # tarik daftar saham IDX resmi
python scripts/backfill_prices.py    # tarik harga historis
python scripts/screen.py             # screener likuiditas -> focus_list
python scripts/fetch_fundamentals.py # rasio fundamental (mingguan, berubah pelan)
python scripts/backtest.py           # backtest engine
```
