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

**Otomatis tiap pagi:** [`run_daily.bat`](run_daily.bat) sudah terpasang di Windows Task
Scheduler (task `TradeDailyBrief`, Sen–Jum 08:00) — langkah 1 jalan sendiri, log ke
`data/daily_log.txt`. Langkah 2 (`/analisa`) tetap manual *by design*: buat duit beneran,
sesi Claude yang baca artikel & mutusin tiap pagi itu **fitur**, bukan kekurangan.

## Ritme operasional (cheatsheet)

Sistem udah kelar (Fase 0–5). Sekarang tinggal **dipakai** — low-maintenance.

**Tiap pagi hari bursa:**
- [ ] Data ketarik SENDIRI jam 08:00 (Task Scheduler `TradeDailyBrief`) — nggak usah ngapa-ngapain
- [ ] Buka Claude Code → ketik **`/analisa`** (Claude baca data + artikel asli → update keputusan)
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
# laporan P/L + bandingin sama sinyal sistem
python scripts/journal.py
```

Muncul juga di tab **Jurnal** dashboard: posisi terbuka + P/L + sinyal sistem terkini +
alarm kalau harga di bawah stop. Data jurnal **privat** (di `data/trade.db`, gitignored).

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
`action`: BELI / TUNGGU PULLBACK / HINDARI · `flag`: good / neutral / caution / danger.

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
  indicators.py   MA / RSI / ATR
  signals.py      signal engine (teknikal + sentimen)
  backtest.py     backtest point-in-time (trailing + biaya)
  paper.py        simulasi portfolio paper
  journal.py      jurnal trading real (Fase 5): P/L + evaluasi vs sinyal
  screener.py     screener likuiditas -> focus_list
  universe.py     ambil daftar saham IDX resmi
scripts/          entry point (daily.py orkestrator, brief.py, dll.)
config/           watchlist.yaml
data/             trade.db, analysis.json, brief_*.md, *.csv  (di-gitignore)
dashboard.py      Streamlit
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
