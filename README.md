# Trade — Analisis Saham berbasis Harga + Berita/Sentimen

Project buat bantu keputusan **beli/jual saham** (swing trading, harian–mingguan)
berbasis **berita + sentimen + fundamental + teknikal**. **Fokus: saham Indonesia (IDX)**
— backtest 5 tahun nunjukin IDX punya edge, US enggak. Kode tetap market-agnostic
(atur di `trade/config.py` → `MARKETS`; US bisa diaktifin lagi kapan aja).

> ⚠️ Bukan nasihat keuangan. Sistem ini alat bantu keputusan, bukan mesin ATM.
> Jalur wajib sebelum pakai duit beneran: **backtest → paper trading → duit kecil.**

## Status: Fase 0 — Data Pipeline ✅

Yang udah jalan sekarang:
- Tarik **harga historis** (yfinance) buat US & IDX
- Tarik **berita** (Google News RSS, gratis tanpa API key)
- Simpan rapi ke **SQLite** (`data/trade.db`)

Roadmap berikutnya: Fase 1 (sentiment engine) → Fase 2 (sinyal) → Fase 3 (backtest) → Fase 4 (paper trade) → Fase 5 (live).

## Setup

```bash
# 1. Bikin virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows PowerShell/CMD

# 2. Install dependency
pip install -r requirements.txt
```

## Jalanin

```bash
# Sekali gas: tarik harga + berita semua saham, simpan ke DB
python scripts/run_all.py
```

Atau per bagian:

```bash
python scripts/init_db.py        # bikin DB + daftarin saham
python scripts/fetch_prices.py   # tarik harga aja
python scripts/fetch_news.py     # tarik berita aja
```

## Atur saham yang dipantau

Edit [`config/watchlist.yaml`](config/watchlist.yaml). Tinggal copy satu blok, ganti isinya.
- US: ticker biasa (`AAPL`)
- IDX: pakai suffix `.JK` (`BBCA.JK`)

## Struktur

```
trade/          package inti (market-agnostic)
  config.py     path + load watchlist
  db.py         SQLite: skema + simpan
  prices.py     tarik harga (yfinance)
  news.py       tarik berita (Google News RSS)
scripts/        entry point yang dijalanin
config/         watchlist.yaml
data/           trade.db (dibikin otomatis, di-gitignore)
```
