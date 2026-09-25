"""api.py — backend FastAPI buat app mobile Trade IDX.

Nyediain: hasil analisa terbaru, jalanin auto_analisa on-demand, atur LLM
(bongkar-pasang provider + key), dan jurnal real (catat / tutup / hapus). Badan artikel
dibaca lokal (trafilatura) — jadi satu-satunya API eksternal = LLM yang dipilih di /config/llm.

KUNCI AKSES: kalau TRADE_API_TOKEN diisi di .env (WAJIB di server cloud), semua endpoint
kecuali /health minta header `X-Token`. Kosong = bebas (mode PC rumah).

Jalanin:
  .venv/Scripts/python.exe -m uvicorn backend.api:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import subprocess
import sys
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
ANALYSIS = BASE / "data" / "analysis.json"
DB = BASE / "data" / "trade.db"
ENV = BASE / ".env"


def db() -> sqlite3.Connection:
    """Koneksi read-only ke trade.db (row = dict-like)."""
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def db_rw() -> sqlite3.Connection:
    """Koneksi TULIS ke trade.db — cuma dipakai endpoint jurnal."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

from trade import journal as jr, llm  # noqa: E402
from trade.risk import trailing_stop_level  # noqa: E402


# ---------------------------------------------------------------- .env helpers
def read_env() -> dict:
    d: dict[str, str] = {}
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if s and not s.startswith("#") and "=" in s:
                k, v = s.split("=", 1)
                d[k.strip()] = v.strip()
    return d


def write_env(updates: dict) -> None:
    lines = ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []
    done, out = set(), []
    for line in lines:
        s = line.strip()
        if s and not s.startswith("#") and "=" in s and s.split("=", 1)[0].strip() in updates:
            k = s.split("=", 1)[0].strip()
            out.append(f"{k}={updates[k]}")
            done.add(k)
        else:
            out.append(line)
    for k, v in updates.items():
        if k not in done:
            out.append(f"{k}={v}")
    ENV.write_text("\n".join(out) + "\n", encoding="utf-8")


# ---------------------------------------------------------------- kunci akses
API_TOKEN = os.environ.get("TRADE_API_TOKEN") or read_env().get("TRADE_API_TOKEN", "")


def require_token(request: Request) -> None:
    """Server publik: tanpa kunci, orang lain bisa hapus jurnal / ganti API key LLM."""
    if not API_TOKEN or request.url.path == "/health":
        return
    if not secrets.compare_digest(request.headers.get("x-token", ""), API_TOKEN):
        raise HTTPException(401, "Kunci akses salah atau kosong. Isi 'Kunci Akses' di Pengaturan app.")


app = FastAPI(title="Trade IDX API", version="0.1.0", dependencies=[Depends(require_token)])
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ---------------------------------------------------------------- endpoints
@app.get("/health")
def health():
    return {"ok": True, "analysis_ready": ANALYSIS.exists()}


@app.get("/analysis")
def get_analysis():
    """Hasil analisa terbaru (data/analysis.json)."""
    if not ANALYSIS.exists():
        raise HTTPException(404, "Belum ada analisa. POST /analisa dulu.")
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


def _friendly_error(output: str) -> tuple[int, str]:
    """Terjemahin output error auto_analisa ke pesan yang kebaca user di app."""
    o = output or ""
    lo = o.lower()
    if "429" in o or "quota" in lo or "resource_exhausted" in lo or "rate limit" in lo:
        return 429, ("Kuota LLM habis (limit gratis hari ini tercapai). Tunggu reset harian, "
                     "atau ganti provider/model di menu Pengaturan (mis. Groq — gratis & cepat).")
    if "api_key_invalid" in lo or "permission_denied" in lo or "401" in o or "api key" in lo:
        return 401, "API key LLM belum bener/kosong. Isi ulang di menu Pengaturan."
    if "timeout" in lo or "timed out" in lo:
        return 504, "LLM kelamaan gak balas (timeout). Coba lagi sebentar."
    tail = o.strip().splitlines()[-1][:200] if o.strip() else "error tak dikenal"
    return 500, f"Analisa gagal: {tail}"


@app.post("/analisa")
def run_analisa(modal: str | None = None):
    """Jalanin auto_analisa (baca data+berita -> LLM -> tulis analysis.json). ~1-2 menit."""
    cmd = [sys.executable, str(BASE / "scripts" / "auto_analisa.py"), "--out", str(ANALYSIS)]
    if modal:
        cmd += ["--modal", modal]
    try:
        p = subprocess.run(cmd, cwd=str(BASE), capture_output=True, text=True, timeout=420)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Analisa timeout (>7 menit). Coba lagi sebentar.")
    if p.returncode != 0:
        code, msg = _friendly_error(p.stderr or p.stdout)
        raise HTTPException(code, msg)
    return json.loads(ANALYSIS.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- data tab (Sinyal/Berita/Chart)
@app.get("/signals")
def get_signals(limit: int = 40):
    """Sinyal mesin per saham, urut skor tertinggi (buat tab Sinyal)."""
    conn = db()
    try:
        asof = conn.execute("SELECT MAX(asof) FROM signals").fetchone()[0]
        rows = conn.execute(
            "SELECT ticker,action,score,close,ma20,ma50,rsi,sent,n_news,stop,target,reasons "
            "FROM signals ORDER BY score DESC LIMIT ?", (limit,)).fetchall()
    finally:
        conn.close()
    out = []
    for r in rows:
        try:
            reasons = json.loads(r["reasons"]) if r["reasons"] else []
        except Exception:
            reasons = []
        d = dict(r)
        d["reasons"] = reasons
        out.append(d)
    return {"asof": asof, "signals": out}


@app.get("/news")
def get_news(ticker: str | None = None, limit: int = 40):
    """Berita terbaru + skor sentimen (lexicon). Plus ringkasan sentimen per saham."""
    conn = db()
    try:
        params: list = []
        where = "WHERE title IS NOT NULL"
        if ticker:
            t = ticker.upper()
            t = t if t.endswith(".JK") else t + ".JK"
            where += " AND ticker=?"
            params.append(t)
        items = conn.execute(
            f"SELECT ticker,published,title,source,link,sent_label,sent_score "
            f"FROM news {where} ORDER BY published DESC LIMIT ?", (*params, limit)).fetchall()
        # ringkasan: rata-rata sentimen per saham (14 hari, min 2 berita) -> top +/-
        agg = conn.execute(
            "SELECT ticker, AVG(sent_score) avg_s, COUNT(*) n "
            "FROM news WHERE published >= date('now','-14 days') AND sent_score IS NOT NULL "
            "GROUP BY ticker HAVING n >= 2 ORDER BY avg_s DESC").fetchall()
    finally:
        conn.close()
    movers = [{"ticker": a["ticker"], "avg": round(a["avg_s"], 3), "n": a["n"]} for a in agg]
    return {
        "items": [dict(r) for r in items],
        "positif": movers[:5],
        "negatif": [m for m in reversed(movers) if m["avg"] < 0][:5],
    }


@app.get("/prices")
def get_prices(ticker: str, days: int = 90):
    """Deret harga harian (OHLC) + level dari sinyal (buat tab Chart)."""
    t = ticker.upper()
    t = t if t.endswith(".JK") else t + ".JK"
    conn = db()
    try:
        rows = conn.execute(
            "SELECT date,open,high,low,close FROM prices WHERE ticker=? ORDER BY date DESC LIMIT ?",
            (t, days)).fetchall()
        sig = conn.execute(
            "SELECT action,score,rsi,ma20,ma50,sent,n_news,stop,target FROM signals WHERE ticker=?",
            (t,)).fetchone()
    finally:
        conn.close()
    if not rows:
        raise HTTPException(404, f"Gak ada data harga buat {t}")
    series = [dict(r) for r in reversed(rows)]  # urut lama -> baru
    last, first = series[-1]["close"], series[0]["close"]
    return {
        "ticker": t,
        "days": len(series),
        "last": last,
        "chg_pct": round((last / first - 1) * 100, 1) if first else None,
        "series": series,
        "levels": {"ma20": sig["ma20"], "ma50": sig["ma50"],
                   "stop": sig["stop"], "target": sig["target"]} if sig else {},
        "signal": {"action": sig["action"], "score": sig["score"], "rsi": sig["rsi"],
                   "sent": sig["sent"], "n_news": sig["n_news"]} if sig else None,
    }


# label + unit buat tiap ticker makro (urutan = urutan tampil di app)
MACRO_LABELS = {
    "GC=F": ("Emas", "$"),
    "IDR=X": ("USD/IDR", ""),
    "^JKSE": ("IHSG", ""),
    "CL=F": ("Minyak", "$"),
    "DX-Y.NYB": ("DXY", ""),
    "^TNX": ("US 10Y", "%"),
    "^VIX": ("VIX", ""),
}


@app.get("/macro")
def get_macro():
    """Angka makro/komoditas harian + perubahan (buat strip di card Makro)."""
    conn = db()
    try:
        out = []
        for tk, (label, unit) in MACRO_LABELS.items():
            rows = conn.execute(
                "SELECT date,close FROM macro WHERE ticker=? ORDER BY date DESC LIMIT 2", (tk,)
            ).fetchall()
            if not rows:
                continue
            last = rows[0]["close"]
            prev = rows[1]["close"] if len(rows) > 1 else last
            chg = round((last / prev - 1) * 100, 2) if prev else 0.0
            out.append({"ticker": tk, "label": label, "unit": unit,
                        "last": last, "chg": chg, "date": rows[0]["date"]})
    finally:
        conn.close()
    return {"items": out}


# ---------------------------------------------------------------- jurnal real (catat / tutup / hapus)
class TradeIn(BaseModel):
    ticker: str
    entry: float
    lot: int
    stop: float | None = None
    target: float | None = None
    thesis: str | None = None
    entry_date: str | None = None


class CloseIn(BaseModel):
    exit: float
    exit_date: str | None = None


def _iso_date(s: str | None, label: str) -> str | None:
    """'2026-09-25' -> dicek formatnya & gak boleh masa depan. Kosong -> None (= hari ini)."""
    if not s or not s.strip():
        return None
    try:
        d = date.fromisoformat(s.strip())
    except ValueError:
        raise HTTPException(400, f"{label} harus format TTTT-BB-HH (mis. 2026-09-25).")
    if d > date.today():
        raise HTTPException(400, f"{label} gak boleh di masa depan.")
    return d.isoformat()


@app.get("/journal")
def get_journal():
    """Isi jurnal real + P/L (posisi terbuka pakai close terakhir) + garis jual trailing."""
    conn = db()
    try:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM journal "
            "ORDER BY status='closed', COALESCE(exit_date, entry_date) DESC, id DESC")]
        px: dict[str, float] = {}
        px_date: dict[str, str] = {}
        trail: dict[int, float | None] = {}
        for r in rows:
            if r["status"] != "open":
                continue
            if r["ticker"] not in px:
                last = conn.execute(
                    "SELECT close, date FROM prices WHERE ticker=? ORDER BY date DESC LIMIT 1",
                    (r["ticker"],)).fetchone()
                if last:
                    px[r["ticker"]], px_date[r["ticker"]] = last["close"], last["date"]
            trail[r["id"]] = trailing_stop_level(conn, r["ticker"], r["entry_date"], r["stop"])["trail"]
    finally:
        conn.close()
    trades = [{**r, **jr.pl(r, px.get(r["ticker"])),
               "px_date": px_date.get(r["ticker"]), "trail": trail.get(r["id"])} for r in rows]
    return {"trades": trades, "summary": jr.summary(rows, px)}


@app.post("/journal")
def add_journal(t: TradeIn):
    """Catat posisi baru (yang UDAH dibeli di broker)."""
    tk = jr.norm_ticker(t.ticker)
    if t.entry <= 0 or t.lot <= 0:
        raise HTTPException(400, "Harga beli & jumlah lot harus lebih dari 0.")
    if t.stop and t.stop >= t.entry:
        raise HTTPException(400, "Stop (rem rugi) harus di BAWAH harga beli.")
    if t.target and t.target <= t.entry:
        raise HTTPException(400, "Target harus di ATAS harga beli.")
    entry_date = _iso_date(t.entry_date, "Tanggal beli")
    conn = db_rw()
    try:
        if not conn.execute("SELECT 1 FROM prices WHERE ticker=? LIMIT 1", (tk,)).fetchone():
            raise HTTPException(400, f"Kode {tk.replace('.JK', '')} gak dikenal (gak ada data harganya).")
        new_id = jr.add_trade(conn, tk, t.entry, t.lot, entry_date, t.stop or None,
                              t.target or None, (t.thesis or "").strip() or None)
    finally:
        conn.close()
    return {"ok": True, "id": new_id}


@app.post("/journal/{trade_id}/close")
def close_journal(trade_id: int, c: CloseIn):
    """Tutup posisi (udah dijual di broker) -> jadi realized P/L."""
    if c.exit <= 0:
        raise HTTPException(400, "Harga jual harus lebih dari 0.")
    exit_date = _iso_date(c.exit_date, "Tanggal jual")
    conn = db_rw()
    try:
        row = conn.execute("SELECT entry_date FROM journal WHERE id=? AND status='open'",
                           (trade_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"Posisi #{trade_id} gak ketemu atau udah ditutup.")
        if exit_date and exit_date < row["entry_date"][:10]:
            raise HTTPException(400, "Tanggal jual gak boleh sebelum tanggal beli.")
        jr.close_trade(conn, trade_id, c.exit, exit_date)
    finally:
        conn.close()
    return {"ok": True}


@app.delete("/journal/{trade_id}")
def delete_journal(trade_id: int):
    """Hapus catatan (salah input / dobel). Permanen."""
    conn = db_rw()
    try:
        n = jr.delete_trade(conn, trade_id)
    finally:
        conn.close()
    if not n:
        raise HTTPException(404, f"Catatan #{trade_id} gak ketemu.")
    return {"ok": True}


# ---------------------------------------------------------------- config LLM
class LLMConfig(BaseModel):
    provider: str
    model: str
    api_key: str | None = None
    base_url: str | None = None


@app.get("/config/llm")
def get_llm():
    """Config LLM aktif + daftar provider (buat menu Pengaturan di app). Key TIDAK dibocorin."""
    env = read_env()
    c = llm.resolve(env)
    return {
        "provider": c["provider"], "model": c["model"], "label": c["label"],
        "base_url": env.get("LLM_BASE_URL", ""), "has_key": bool(c["key"]),
        "providers": {k: {"label": v["label"], "models": v["models"],
                          "key_url": v["key_url"], "openai": v["openai"]}
                      for k, v in llm.PROVIDERS.items()},
    }


@app.post("/config/llm")
def set_llm(cfg: LLMConfig):
    upd = {"LLM_PROVIDER": cfg.provider, "LLM_MODEL": cfg.model}
    if cfg.api_key is not None:
        upd["LLM_API_KEY"] = cfg.api_key
    if cfg.base_url is not None:
        upd["LLM_BASE_URL"] = cfg.base_url
    write_env(upd)
    return {"ok": True}


@app.post("/config/llm/test")
def test_llm():
    ok, msg = llm.test_connection(read_env())
    return {"ok": ok, "message": msg}
