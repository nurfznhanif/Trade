"""auto_analisa.py — otak analisa harian: data + ISI berita -> LLM -> data/analysis.json (dibaca app).

Server jalanin ini tiap Senin-Jumat 05:00 WIB, habis scripts/daily.py (systemd trade-daily) —
JANGAN pindah/rename file ini. Isi artikel dibaca LOKAL (trade/newsbody.py, tanpa API), jadi
API eksternal cuma LLM. Provider + key diatur dari menu Pengaturan app (tersimpan di .env).

  python scripts/auto_analisa.py                  # analisa penuh -> data/analysis.json
  python scripts/auto_analisa.py --test           # tes koneksi LLM aktif
  python scripts/auto_analisa.py --list-models    # daftar model provider aktif
  python scripts/auto_analisa.py --provider deepseek --model deepseek-v4-pro
"""
from __future__ import annotations

import _bootstrap  # noqa: F401  (path repo + UTF-8)

import argparse
import json
import os
import re
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from trade import llm, rapor
from trade.config import ANALYSIS_PATH, BRIEF_PATH, read_env
from trade.db import get_connection
from trade.indicators import rsi, sma
from trade.journal import report
from trade.msci import msci_status
from trade.newsbody import bodies_for
from trade.ticks import round_levels


# ---------------------------------------------------------------- kumpulin data
def big_cap_block(conn: sqlite3.Connection) -> str:
    """Lensa big cap: 15 saham turnover terbesar + skor mesin + berita."""
    sig = {r["ticker"]: (r["score"], r["action"])
           for r in conn.execute("SELECT ticker,score,action FROM signals")}
    q = ("WITH r AS (SELECT ticker,close,volume,ROW_NUMBER() OVER "
         "(PARTITION BY ticker ORDER BY date DESC) rn FROM prices) "
         "SELECT ticker,AVG(close*volume) turn,MAX(CASE WHEN rn=1 THEN close END) last "
         "FROM r WHERE rn<=20 GROUP BY ticker ORDER BY turn DESC LIMIT 15")
    s = (datetime.now(timezone.utc) - timedelta(days=12)).isoformat()
    out = ["## LENSA BIG CAP (turnover terbesar — nilai dari valuasi+berita, bukan cuma momentum)"]
    for b in conn.execute(q):
        # teknikal ringkas biar model bisa terapin aturan RSI>70 / tren
        cl = [r[0] for r in conn.execute(
            "SELECT close FROM prices WHERE ticker=? ORDER BY date", (b["ticker"],))]
        tech = ""
        if len(cl) >= 50:
            chg = (cl[-1] / cl[-21] - 1) * 100 if len(cl) > 21 else 0
            tren = "uptrend" if cl[-1] > sma(cl, 20) > sma(cl, 50) else (
                "downtrend" if cl[-1] < sma(cl, 20) < sma(cl, 50) else "sideways")
            tech = f"  RSI {rsi(cl, 14):.0f} · {tren} · 1bln {chg:+.0f}%"
        out.append(f"### {b['ticker']}  ~Rp{b['turn']/1e9:.1f}M/hari  last {int(b['last'])}  "
                   f"[mesin {sig.get(b['ticker'], '-')}]{tech}")
        for x in conn.execute(
                "SELECT published,title FROM news WHERE ticker=? AND title IS NOT NULL "
                "AND (published IS NULL OR published>=?) ORDER BY published DESC LIMIT 4",
                (b["ticker"], s)):
            out.append(f"  [{(x['published'] or '')[:10]}] {x['title']}")
    return "\n".join(out)


def positions_block(conn: sqlite3.Connection) -> str:
    """Posisi terbuka di jurnal + garis jual trailing + harga terakhir (buat verdict TAHAN/WASPADA/JUAL)."""
    opened = [t for t in report(conn)["trades"] if t["status"] == "open" and t["px"] is not None]
    if not opened:
        return ""
    out = ["## POSISI TERBUKA (journal) — kasih verdict TAHAN/WASPADA/JUAL"]
    for t in opened:
        tr = t["trail"]
        above = (t["px"] / tr - 1) * 100 if tr else 0
        out.append(f"  {t['ticker']}: last {int(t['px'])}  trail {int(tr or 0)}  "
                   f"({above:+.1f}% di atas trail)  entry {int(t['entry'])}")
    return "\n".join(out)


def gather_context(conn: sqlite3.Connection) -> tuple[str, str]:
    """Balikin (blok_konteks, tanggal_data). Backbone = brief_latest.md (ditulis daily.py)."""
    brief = BRIEF_PATH.read_text(encoding="utf-8") if BRIEF_PATH.exists() else "(brief tidak ada)"
    data_date = conn.execute("SELECT MAX(date) FROM prices").fetchone()[0]
    top20 = [r[0] for r in conn.execute("SELECT ticker FROM signals ORDER BY score DESC LIMIT 20")]
    parts = [
        f"DATA per: {data_date} | Hari ini: {date.today().isoformat()}",
        f"TOP-20 kandidat by skor mesin: {', '.join(top20)}",
        f"MSCI: {msci_status(date.today())['note']}",
        "",
        "## BRIEF HARIAN (teknikal + fundamental + berita + regime + posisi)",
        brief,
        "",
        big_cap_block(conn),
        "",
        bodies_for(conn, top20[:12]),   # isi artikel top-12 kandidat (dibaca lokal, tanpa API)
        "",
        positions_block(conn),
    ]
    return "\n".join(parts), data_date


# ---------------------------------------------------------------- prompt
SCHEMA_HINT = """
Skema WAJIB (JSON valid, TANPA markdown/```):
{
  "generated": "YYYY-MM-DD",
  "regime": "RISK-ON|RISK-OFF|NETRAL",
  "macro": "cerita pasar, lihat ATURAN MACRO di bawah",
  "calls": [
    {"ticker":"XXXX.JK","action":"BELI|BELI (tenang)|BELI (spekulatif)|TUNGGU PULLBACK|HINDARI",
     "conviction":"Tinggi|Sedang-Tinggi|Sedang|-","flag":"good|neutral|caution|danger",
     "entry":int_atau_null,"target":int_atau_null,"stop":int_atau_null,
     "reason":"1-2 kalimat, WAJIB sebut TEMUAN dari ISI berita (bukan cuma judul)"}
  ],
  "positions": [
    {"ticker":"XXXX.JK","verdict":"TAHAN|WASPADA|JUAL","reason":"1 kalimat"}
  ]
}
entry/target/stop = integer; HINDARI -> null. Kalau tidak ada posisi terbuka, "positions": [].
JANGAN isi field "lot" — sizing dihitung terpisah oleh kode.

ATURAN MACRO (dibaca investor ritel di HP, harus ENAK DIBACA kayak cerita, BUKAN laporan kilat):
- 2-3 paragraf pendek (2-3 kalimat per paragraf), pisahkan paragraf pakai "\\n\\n".
  Paragraf 1: lagi kayak apa pasar sekarang & kenapa (bahasa sehari-hari).
  Paragraf 2: tema/sentimen yang lagi jalan (sektor panas, arus asing, MSCI kalau relevan).
  Paragraf 3: artinya buat kita & sikap yang disarankan.
- JANGAN deretin angka beruntun (angka makro udah tampil di kartu terpisah). Sebut angka cuma
  kalau penting & langsung jelasin artinya (mis. "rupiah melemah ke 17.875 per dolar — bikin
  saham importir tertekan").
- Istilah teknis dijelasin: "MA200" -> "rata-rata harga 200 hari", "risk-off" -> "investor lagi
  main aman". Jangan pakai label "(jelek)"/"(bagus)".
- "regime" diisi terpisah (RISK-ON/RISK-OFF/NETRAL), gak perlu ditulis kapital di cerita.
"""

RULES = """
Kamu analis saham IDX yang DISIPLIN & SKEPTIS. Putuskan dari DATA + ISI BERITA, BUKAN skor mesin / judul.
Judul media saham Indonesia sering CLICKBAIT. Kamu TIDAK bisa buka artikel (no web), jadi WAJIB skeptis:

SKEPTIS KATALIS-JUDUL (penting, ini sumber jebakan):
- Judul "kerja sama / MOU / teken / gandeng / kolaborasi / bidik / berpotensi / prospek cerah"
  = katalis BELUM TENTU nyata. Tanpa angka konkret (kontrak Rp, laba naik, produksi) di data,
  JANGAN naikin konviksi. Untuk saham yang PER tinggi ATAU sudah naik banyak sebulan,
  katalis-judul begini -> HINDARI atau caution, JANGAN BELI.
- Judul "rights issue / akuisisi / private placement" = waspada DILUSI -> default HINDARI/caution
  kecuali jelas menguntungkan pemegang saham lama.
- "insider/direksi borong" di saham yang sudah pump = TIDAK menutup risiko; tetap waspada.

DISIPLIN KERAS (jangan dilanggar walau skor mesin hijau / big cap):
- RSI > 70 ATAU sudah +25% sebulan -> WAJIB "TUNGGU PULLBACK", DILARANG "BELI" (termasuk bank besar).
- Rugi (margin negatif) / pump / dilusi besar / PER cangkang / suspensi -> HINDARI (flag danger/caution).
- SELEKTIF (regime risk-off): MAKSIMAL ~6-8 "BELI". Kasih "BELI" HANYA kalau ada TEMUAN POSITIF KONKRET
  (laba naik nyata, valuasi murah + katalis jelas, target analis). Nama yang gak bisa kamu dukung
  dengan fakta konkret -> "TUNGGU PULLBACK" atau HINDARI, JANGAN dipaksa "BELI".
- Nama yang beritanya cuma "rekomendasi analis" / partnership samar tanpa substansi -> JANGAN BELI.

Level & exit:
- entry dekat harga sekarang / support; stop di bawah support 20-hari.
- target = CHECKPOINT pertama (bukan jual mati); reason ingatkan TRAILING (geser stop naik), jangan jual pas target.
- Data fundamental yfinance absurd (divyield/PBV/DER ngaco) -> ABAIKAN, sebut kalau relevan.
- BIG CAP (dari lensa) WAJIB dinilai walau mesin HOLD: overbought -> TUNGGU; murah+katalis konkret -> boleh BELI.
- MSCI musim (near) -> ceritain di macro: arus asing big cap bisa gejolak (teknikal).
- reason 1-2 kalimat, konkret dari data. Beri verdict posisi terbuka juga.
Nilai ~15-20 kandidat teratas + semua big cap.
"""


def build_prompt(context: str) -> str:
    return f"{RULES}\n{SCHEMA_HINT}\n\n=== DATA ===\n{context}\n\n=== OUTPUT: JSON saja ==="


def extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        raise ValueError(f"Gak nemu JSON di respons:\n{text[:300]}")
    return json.loads(t[i:j + 1])


# ---------------------------------------------------------------- main
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ANALYSIS_PATH))
    ap.add_argument("--provider", help="override LLM_PROVIDER (deepseek/gemini/openai)")
    ap.add_argument("--model", help="override LLM_MODEL")
    ap.add_argument("--list-models", action="store_true", help="daftar model provider aktif")
    ap.add_argument("--test", action="store_true", help="tes koneksi LLM aktif")
    args = ap.parse_args()

    llm.migrate_env()
    for k, v in read_env().items():      # variabel environment yang udah ada tetap menang
        os.environ.setdefault(k, v)
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider
    if args.model:
        os.environ["LLM_MODEL"] = args.model
    cfg = llm.resolve(os.environ)

    if args.list_models:
        print(f"Model buat {cfg['label']}:")
        for m in llm.list_models(os.environ):
            print("  -", m)
        return
    if args.test:
        print(llm.test_connection(os.environ)[1])
        return

    conn = get_connection()
    context, data_date = gather_context(conn)
    print(f"- data per {data_date} | LLM {cfg['label']} / {cfg['model']}")
    print(f"- context ~{len(context)} char, manggil LLM...", flush=True)
    obj = round_levels(extract_json(llm.generate(build_prompt(context), os.environ)))   # harga sah di broker

    obj.setdefault("generated", date.today().isoformat())
    obj["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")   # app: "pukul HH.MM WIB"
    obj["engine"] = f"{cfg['label']} / {cfg['model']}"
    Path(args.out).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    if Path(args.out).resolve() == ANALYSIS_PATH.resolve():   # analisa utama -> arsip buat Rapor
        try:
            print(f"- diarsip buat Rapor: {rapor.archive(conn, obj)}")
        except Exception as e:                               # arsip gagal gak boleh ngeganggu analisa
            print(f"[!] arsip analisa gagal: {e}")

    calls = obj.get("calls", [])
    print(f"OK {len(calls)} calls -> {args.out}")
    for k, v in sorted(Counter(c.get("action", "?") for c in calls).items()):
        print(f"    {k}: {v}")
    if obj.get("positions"):
        print(f"    positions: {len(obj['positions'])}")


if __name__ == "__main__":
    main()
