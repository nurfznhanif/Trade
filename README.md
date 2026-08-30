# Trade — Analisis Saham IDX (Harga + Berita + Fundamental)

Alat bantu keputusan **beli/jual saham** (swing trading, harian–mingguan) berbasis
**teknikal + sentimen berita + fundamental**, dengan **keputusan akhir dirangkum Claude (LLM)**.
**Fokus: saham Indonesia (IDX)** — backtest 5 tahun nunjukin IDX punya edge, US enggak.
Kode tetap market-agnostic (atur di [`trade/config.py`](trade/config.py) → `MARKETS`).

> ⚠️ **Bukan nasihat keuangan.** Sistem ini alat bantu keputusan, bukan mesin ATM.
> Jalur wajib sebelum pakai duit beneran: **backtest → paper trading → duit kecil.**

## Status: Fase 0–4 ✅ + Dashboard + Brief — operasional

| Fase | Isi | Status |
|------|-----|--------|
| 0 | Data pipeline: harga (yfinance) + berita (Google News RSS) → SQLite | ✅ |
| 1 | Sentiment engine (skor berita −1..+1) | ✅ |
| 2 | Signal engine (teknikal + sentimen → BUY/HOLD/SELL) + pagar fundamental | ✅ |
| 3 | Backtest engine (point-in-time, anti-lookahead, trailing stop + biaya) | ✅ |
| 4 | Paper trading (portfolio FULL vs TECH + benchmark, A/B sentimen) | ✅ |
| — | Dashboard Streamlit + Keputusan Claude (`analysis.json`) + brief harian | ✅ |
| 5 | Live (duit kecil) + jurnal + validasi alpha | ⏳ berikutnya |

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

## Alur harian (4 langkah)

```bash
# 1. Refresh SEMUA data + sinyal + paper trading (sekali gas)
python scripts/daily.py

# 2. Dump brief: semua konteks per-saham jadi 1 file (data/brief_latest.md)
python scripts/brief.py

# 3. Claude baca brief_latest.md -> tulis keputusan ke data/analysis.json
#    (macro + entry/target/stop/reason per saham)

# 4. Lihat dashboard
streamlit run dashboard.py        # -> http://localhost:8501
```

**Otomatis tiap pagi:** pasang [`run_daily.bat`](run_daily.bat) di Windows Task Scheduler
(langkah 1 jalan sendiri, log ke `data/daily_log.txt`). Langkah 3 (Claude) masih manual —
brief bikin cepat; opsi full-auto: panggil Claude API dari script.

## Otak dashboard: `data/analysis.json`

Dashboard menaruh **Keputusan Claude di depan**, sinyal mesin cuma pembanding.
`analysis.json` diisi tiap hari berdasarkan `brief_latest.md`. Formatnya:

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
  indicators.py   MA / RSI / ATR
  signals.py      signal engine (teknikal + sentimen)
  backtest.py     backtest point-in-time (trailing + biaya)
  paper.py        simulasi portfolio paper
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
