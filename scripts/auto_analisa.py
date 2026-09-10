"""auto_analisa.py — versi KODE dari /analisa.

Kumpulin data + BADAN artikel (trade/newsbody.py, lokal tanpa API), panggil LLM
(BONGKAR-PASANG lewat trade/llm.py: Gemini/DeepSeek/OpenAI/Groq/OpenRouter/Ollama)
buat judgment BELI/HINDARI + alasan yang WAJIB baca isi berita, lalu tulis JSON
skema sama yang dipakai dashboard/app.

Ini yang nanti dipanggil TOMBOL di app mobile (lewat backend).

Contoh:
  .venv/Scripts/python.exe scripts/auto_analisa.py                        # analisa penuh
  .venv/Scripts/python.exe scripts/auto_analisa.py --modal 100jt          # + sizing lot
  .venv/Scripts/python.exe scripts/auto_analisa.py --list-models          # daftar model provider aktif
  .venv/Scripts/python.exe scripts/auto_analisa.py --test                 # tes koneksi LLM aktif
  .venv/Scripts/python.exe scripts/auto_analisa.py --provider deepseek --model deepseek-chat
  .venv/Scripts/python.exe scripts/auto_analisa.py --refresh              # tarik data baru dulu (daily.py)

Provider + key diatur di .env (LLM_PROVIDER / LLM_MODEL / LLM_API_KEY / LLM_BASE_URL)
atau lewat menu "Pengaturan LLM" di dashboard. JANGAN hardcode key.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

sys.stdout.reconfigure(encoding="utf-8")  # Windows console kadang cp1252

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))  # biar `import trade...` jalan pas dirun dari mana aja
DB = BASE / "data" / "trade.db"
BRIEF = BASE / "data" / "brief_latest.md"
API_ROOT = "https://generativelanguage.googleapis.com/v1beta"


# ---------------------------------------------------------------- util kecil
def load_env() -> None:
    """Loader .env mini (biar gak butuh python-dotenv)."""
    f = BASE / ".env"
    if not f.exists():
        return
    for line in f.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        import os
        os.environ.setdefault(k.strip(), v.strip())


def parse_modal(s: str | None) -> int | None:
    """'100jt' / '1,5 juta' / '1500000' / '500rb' -> int rupiah."""
    if not s:
        return None
    t = s.lower().replace(" ", "").replace(".", "").replace(",", ".")
    mult = 1
    if "jt" in t or "juta" in t:
        mult = 1_000_000
        t = t.replace("juta", "").replace("jt", "")
    elif "rb" in t or "ribu" in t:
        mult = 1_000
        t = t.replace("ribu", "").replace("rb", "")
    m = re.search(r"[\d.]+", t)
    if not m:
        return None
    return int(float(m.group()) * mult)


# ---------------------------------------------------------------- kumpulin data
def big_cap_block(conn: sqlite3.Connection) -> str:
    """Lensa big cap: 15 saham turnover terbesar + skor mesin + berita."""
    conn.row_factory = sqlite3.Row
    sig = {r["ticker"]: (r["score"], r["action"])
           for r in conn.execute("SELECT ticker,score,action FROM signals")}
    q = ("WITH r AS (SELECT ticker,close,volume,ROW_NUMBER() OVER "
         "(PARTITION BY ticker ORDER BY date DESC) rn FROM prices) "
         "SELECT ticker,AVG(close*volume) turn,MAX(CASE WHEN rn=1 THEN close END) last "
         "FROM r WHERE rn<=20 GROUP BY ticker ORDER BY turn DESC LIMIT 15")
    s = (datetime.now(timezone.utc) - timedelta(days=12)).isoformat()
    from trade.indicators import sma, rsi as rsi_f
    out = ["## LENSA BIG CAP (turnover terbesar — nilai dari valuasi+berita, bukan cuma momentum)"]
    for b in conn.execute(q):
        # teknikal ringkas biar model bisa terapin aturan RSI>70 / tren
        cl = [r[0] for r in conn.execute(
            "SELECT close FROM prices WHERE ticker=? ORDER BY date", (b["ticker"],))]
        tech = ""
        if len(cl) >= 50:
            r14 = rsi_f(cl, 14)
            chg = (cl[-1] / cl[-21] - 1) * 100 if len(cl) > 21 else 0
            tren = "uptrend" if cl[-1] > sma(cl, 20) > sma(cl, 50) else (
                "downtrend" if cl[-1] < sma(cl, 20) < sma(cl, 50) else "sideways")
            tech = f"  RSI {r14:.0f} · {tren} · 1bln {chg:+.0f}%"
        out.append(f"### {b['ticker']}  ~Rp{b['turn']/1e9:.1f}M/hari  last {int(b['last'])}  [mesin {sig.get(b['ticker'],'-')}]{tech}")
        for x in conn.execute(
                "SELECT published,title FROM news WHERE ticker=? AND title IS NOT NULL "
                "AND (published IS NULL OR published>=?) ORDER BY published DESC LIMIT 4",
                (b["ticker"], s)):
            out.append(f"  [{(x['published'] or '')[:10]}] {x['title']}")
    return "\n".join(out)


def positions_block(conn: sqlite3.Connection) -> str:
    """Posisi terbuka + trailing stop + harga terakhir (buat review TAHAN/WASPADA/JUAL)."""
    try:
        from trade.risk import trailing_stop_level
    except Exception:
        return ""
    conn.row_factory = sqlite3.Row
    rows = list(conn.execute(
        "SELECT ticker,entry_date,entry,stop FROM journal WHERE status='open'"))
    if not rows:
        return ""
    out = ["## POSISI TERBUKA (journal) — kasih verdict TAHAN/WASPADA/JUAL"]
    for r in rows:
        px = list(conn.execute(
            "SELECT close FROM prices WHERE ticker=? ORDER BY date DESC LIMIT 1", (r["ticker"],)))
        if not px:
            continue
        last = px[0]["close"]
        d = trailing_stop_level(conn, r["ticker"], r["entry_date"], r["stop"])
        tr = d["trail"]
        vt = (last / tr - 1) * 100 if tr else 0
        out.append(f"  {r['ticker']}: last {int(last)}  trail {int(tr)}  ({vt:+.1f}% di atas trail)  entry {int(r['entry'])}")
    return "\n".join(out)


def gather_context(conn: sqlite3.Connection) -> tuple[str, str]:
    """Balikin (blok_konteks, tanggal_data). Backbone = brief_latest.md."""
    brief = BRIEF.read_text(encoding="utf-8") if BRIEF.exists() else "(brief tidak ada)"
    data_date = conn.execute("SELECT MAX(date) FROM prices").fetchone()[0]
    top20 = [r[0] for r in conn.execute(
        "SELECT ticker FROM signals ORDER BY score DESC LIMIT 20")]
    from trade.msci import msci_status
    msci = msci_status(date.today())["note"]

    # baca badan artikel LOKAL (decode Google News + trafilatura, TANPA API) — top-12 kandidat
    from trade.newsbody import bodies_for
    body_block = bodies_for(conn, top20[:12])

    parts = [
        f"DATA per: {data_date} | Hari ini: {date.today().isoformat()}",
        f"TOP-20 kandidat by skor mesin: {', '.join(top20)}",
        f"MSCI: {msci}",
        "",
        "## BRIEF HARIAN (teknikal + fundamental + berita + regime + posisi)",
        brief,
        "",
        big_cap_block(conn),
        "",
        body_block,
        "",
        positions_block(conn),
    ]
    return "\n".join(parts), data_date


# ---------------------------------------------------------------- prompt
SCHEMA_HINT = """
Skema WAJIB (JSON valid, TANPA markdown/```):
{
  "generated": "YYYY-MM-DD",
  "engine": "Gemini (LLM) — baca data + berita",
  "macro": "1-3 kalimat: regime IHSG + tema panas + sikap + status MSCI",
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
- MSCI musim (near) -> ingatkan di macro: arus asing big cap bisa gejolak (teknikal).
- reason 1-2 kalimat, konkret dari data. Beri verdict posisi terbuka juga.
Nilai ~15-20 kandidat teratas + semua big cap.
"""


def build_prompt(context: str, modal: int | None) -> str:
    modal_note = ""
    if modal:
        modal_note = (f"\nModal user Rp{modal:,} — tetap kasih entry/stop realistis; "
                      "sizing lot dihitung kode, kamu fokus keputusan+alasan.")
    return f"{RULES}\n{SCHEMA_HINT}{modal_note}\n\n=== DATA ===\n{context}\n\n=== OUTPUT: JSON saja ==="


def extract_json(text: str) -> dict:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t).strip()
    i, j = t.find("{"), t.rfind("}")
    if i == -1 or j == -1:
        raise ValueError(f"Gak nemu JSON di respons:\n{text[:300]}")
    return json.loads(t[i:j + 1])


# ---------------------------------------------------------------- sizing
def apply_sizing(obj: dict, modal: int | None, risk: float) -> None:
    if not modal:
        return
    from trade.risk import position_size
    obj["modal"] = modal
    for c in obj.get("calls", []):
        act = (c.get("action") or "")
        if act.startswith("BELI") and c.get("entry") and c.get("stop"):
            r = risk / 2 if "spekulatif" in act.lower() else risk  # spek: setengah ukuran
            try:
                c["lot"] = position_size(modal, int(c["entry"]), int(c["stop"]), risk_pct=r)["lot"]
            except Exception:
                c["lot"] = 0


# ---------------------------------------------------------------- main
def main() -> None:
    load_env()
    import os
    from trade import llm
    ap = argparse.ArgumentParser()
    ap.add_argument("--modal", help="mis. 100jt / 1500000 / 1,5juta")
    ap.add_argument("--risk", type=float, default=0.02, help="risiko per trade (default 0.02)")
    ap.add_argument("--out", default=str(BASE / "data" / "analysis_gemini.json"))
    ap.add_argument("--provider", help="override LLM_PROVIDER (gemini/deepseek/openai/groq/openrouter/ollama/custom)")
    ap.add_argument("--model", help="override LLM_MODEL")
    ap.add_argument("--refresh", action="store_true", help="jalanin daily.py dulu")
    ap.add_argument("--list-models", action="store_true", help="daftar model provider aktif")
    ap.add_argument("--test", action="store_true", help="tes koneksi LLM aktif")
    args = ap.parse_args()

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
        ok, msg = llm.test_connection(os.environ)
        print(msg)
        return

    if args.refresh:
        print("refresh data (daily.py)…")
        subprocess.run([sys.executable, str(BASE / "scripts" / "daily.py")], check=False)

    conn = sqlite3.connect(DB)
    context, data_date = gather_context(conn)
    modal = parse_modal(args.modal)
    print(f"• data per {data_date} | LLM {cfg['label']} / {cfg['model']}"
          + (f" | modal Rp{modal:,}" if modal else ""))

    prompt = build_prompt(context, modal)
    print(f"• context ~{len(context)} char, manggil LLM…")
    text = llm.generate(prompt, os.environ)
    obj = extract_json(text)

    obj.setdefault("generated", date.today().isoformat())
    apply_sizing(obj, modal, args.risk)

    Path(args.out).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

    calls = obj.get("calls", [])
    from collections import Counter
    dist = Counter(c.get("action", "?") for c in calls)
    print(f"✓ {len(calls)} calls -> {args.out}")
    for k, v in sorted(dist.items()):
        print(f"    {k}: {v}")
    if obj.get("positions"):
        print(f"    positions: {len(obj['positions'])}")


if __name__ == "__main__":
    main()
