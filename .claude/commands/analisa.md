---
description: Analisa harian saham IDX — baca data folder + artikel berita ASLI, tulis data/analysis.json
argument-hint: "[ticker opsional, mis. BBRI = deep-dive 1 saham]"
---

Kamu lagi ngerjain **ANALISA HARIAN SAHAM IDX** buat project ini. Hasil akhir: file
`data/analysis.json` yang dibaca dashboard Streamlit. Inti aturannya:

> **KAMU (LLM) yang mutusin — dengan baca DATA + ISI ARTIKEL berita beneran, BUKAN skor
> rule-based/lexicon. Judul media saham Indonesia sering clickbait: SELALU cross-check ke badan berita.**

Argumen: `$ARGUMENTS` — kalau diisi ticker (mis. `BBRI`), fokus deep-dive saham itu.
Kalau kosong, jalanin analisa harian penuh (semua kandidat teratas).

## Langkah

**1. Baca data folder (sari pati).**
- Baca `data/brief_latest.md` (output pipeline: teknikal + fundamental + headline per kandidat).
  Catat baris "data per ...". Kalau tanggalnya lebih tua dari hari bursa terakhir → kasih tahu
  user datanya basi & saranin jalanin `.venv/Scripts/python.exe scripts/daily.py` dulu.
- Tarik headline + info tambahan kandidat teratas dari DB:
  ```
  .venv/Scripts/python.exe -c "import sqlite3;from datetime import datetime,timedelta,timezone;c=sqlite3.connect('data/trade.db');c.row_factory=sqlite3.Row;top=[r['ticker'] for r in c.execute('SELECT ticker FROM signals ORDER BY score DESC LIMIT 12')];s=(datetime.now(timezone.utc)-timedelta(days=12)).isoformat();[print('\n###',t) or [print(' [',(x['published'] or '')[:10],']',x['title']) for x in c.execute('SELECT published,title FROM news WHERE ticker=? AND title IS NOT NULL AND (published IS NULL OR published>=?) ORDER BY published DESC LIMIT 8',(t,s))] for t in top]"
  ```

**2. BACA ARTIKEL ASLI — langkah KUNCI, JANGAN di-skip.**
Untuk tiap kandidat kuat (±8–12 teratas, atau ticker di `$ARGUMENTS`):
- **WebSearch**: nama perusahaan + ticker + topik (mis. "laba semester", "target harga", "berita terbaru").
- **WebFetch 1–2 artikel media BENERAN** (URL media langsung dari hasil search).
  ⚠️ Link `news.google.com/rss/articles/...` di DB **NGGAK bisa dibuka** (cangkang) — cari URL media aslinya lewat WebSearch.
- Baca **BADAN**-nya: verifikasi angka, cari **caveat/risiko yang disembunyiin judul** —
  kas/arus kas, utang, insider selling, asumsi di balik target analis, suspensi, paywall, dsb.

**3. Baca makro** dari arus berita (arah IHSG, arus asing, tema sektor panas). Jujur: angka
IHSG belum ada di DB, jadi tone makro dibaca dari berita.

**4. Tulis `data/analysis.json`** — skema PERSIS (dibaca dashboard):
```json
{
  "generated": "YYYY-MM-DD",
  "engine": "Claude (LLM) — baca data folder + artikel asli",
  "macro": "ringkas: arah pasar + tema panas + sikap",
  "calls": [
    {"ticker":"XXXX.JK","action":"BELI","conviction":"Tinggi","flag":"good",
     "entry":1000,"target":1200,"stop":950,"reason":"1-2 kalimat, WAJIB sebut temuan dari ISI artikel"}
  ]
}
```
- `action`: `BELI` / `BELI (tenang)` / `BELI (spekulatif)` / `TUNGGU PULLBACK` / `HINDARI`
- `flag`: `good` / `neutral` / `caution` / `danger` · `conviction`: `Tinggi` / `Sedang-Tinggi` / `Sedang` / `-`
- entry/target/stop = integer (HINDARI → `null`).

**Aturan keputusan:**
- entry dekat harga sekarang / area support; stop di bawah support 20-hari.
- **EXIT = TRAILING (penting):** `target` itu CHECKPOINT pertama, BUKAN tempat jual mati.
  Backtest: trailing JAUH > fixed target (avg winner 20% vs 14%, max 425% vs 189%). Di `reason`
  ingetin: "biarin lari — geser stop naik (trailing high−3×ATR), jangan jual pas kena target".
- **MAKRO (regime):** baca REGIME IHSG di brief. Risk-off = lebih SELEKTIF + ukuran lebih KECIL
  (BUKAN stop total — backtest: risk-off masih rata2 +2,86%). Tulis regime + sikap di field `macro`.
- **SIZING:** ingetin user pakai risk-based (risiko 1–2% modal/trade); jarak entry↔stop yang
  nentuin lot, bukan nebak (`python scripts/journal.py size ...` atau kalkulator di dashboard).
- RSI > 70 **atau** sudah +25–30% sebulan → `TUNGGU PULLBACK` (jangan kejar).
- Insider selling / rugi / PER cangkang / pump / suspensi → `HINDARI` atau `caution`, **walau skor mesin hijau**.
- Data fundamental yfinance yang ekstrem/ngaco (PBV/DER/divyield absurd) → ABAIKAN, sebut kalau relevan.
- `reason` **wajib** cerminin isi ARTIKEL, bukan cuma judul.

**5. Validasi & lapor.**
- Validasi JSON: `.venv/Scripts/python.exe -c "import json;print(len(json.load(open('data/analysis.json',encoding='utf-8'))['calls']),'calls OK')"`
- Lapor ke user: ringkasan call (jumlah BELI/TUNGGU/HINDARI) + **clickbait/caveat apa yang ketemu
  dari baca artikel asli** (ini bukti kerjanya). Sertakan link sumber yang dibaca.

## Jangan
- Jangan pakai Claude API / API key — **kamu (sesi ini)** yang ngerjain, pakai langganan user.
- Jangan mutusin cuma dari judul/skor. Kalau nggak sempat baca artikel satu saham, tandai
  konviksinya lebih rendah + bilang ke user.
