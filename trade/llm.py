"""llm.py — lapisan LLM BONGKAR-PASANG: DeepSeek, Gemini, OpenAI (dipilih Bapak, sisanya dihapus Sep 2026).

Dua bentuk API:
  - "gemini"          : Google Generative Language REST
  - OpenAI-compatible : /chat/completions  (DeepSeek, OpenAI)

Config dibaca dari env (diisi lewat .env / menu dashboard / app):
  LLM_PROVIDER      deepseek | gemini | openai
  LLM_MODEL         nama model
  LLM_KEY_<PROV>    API key per provider (LLM_API_KEY = key provider aktif; gemini boleh GEMINI_API_KEY)
  LLM_BASE_URL      override base URL (opsional, biasanya kosong)
"""
from __future__ import annotations

import re
import time

import requests

# preset tiap provider: label, OpenAI-compatible?, base URL, tempat ambil key, contoh model
PROVIDERS: dict[str, dict] = {
    "deepseek": {"label": "DeepSeek", "openai": True, "base": "https://api.deepseek.com",
                 # deepseek-chat/-reasoner DIPENSIUNKAN 24 Jul 2026 (api-docs.deepseek.com)
                 "key_url": "platform.deepseek.com", "models": ["deepseek-flash", "deepseek-v4-pro"]},
    "gemini": {"label": "Google Gemini", "openai": False,
               "base": "https://generativelanguage.googleapis.com/v1beta",
               "key_url": "aistudio.google.com/apikey",
               # per Sep 2026 (ai.google.dev/gemini-api/docs/models): Google nyaranin 3.8 Flash / 3.5 Flash-Lite
               "models": ["gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.5-flash",
                          "gemini-flash-latest"]},
    "openai": {"label": "OpenAI", "openai": True, "base": "https://api.openai.com/v1",
               # per Sep 2026 (developers.openai.com/api/docs/pricing) — yang murah dulu
               "key_url": "platform.openai.com/api-keys",
               "models": ["gpt-6-luna", "gpt-5.6-luna", "gpt-5-mini", "gpt-6-sol", "gpt-5.6-terra"]},
}


def resolve(env: dict) -> dict:
    """Config efektif dari env -> {provider, openai, base, key, model, label}."""
    provider = (env.get("LLM_PROVIDER") or "gemini").strip().lower()
    p = PROVIDERS.get(provider, PROVIDERS["gemini"])
    # key per provider (LLM_KEY_DEEPSEEK dst) -> fallback key aktif lama (LLM_API_KEY)
    key = (env.get(f"LLM_KEY_{provider.upper()}") or env.get("LLM_API_KEY") or "").strip()
    if not key and provider == "gemini":
        key = (env.get("GEMINI_API_KEY") or "").strip()      # backward-compat
    model = (env.get("LLM_MODEL") or "").strip() or (p["models"][0] if p["models"] else "")
    base = (env.get("LLM_BASE_URL") or "").strip() or p["base"]
    return {"provider": provider, "openai": p["openai"], "base": base,
            "key": key, "model": model, "label": p["label"]}


def _post(url: str, headers: dict, body: dict, tries: int = 4) -> requests.Response:
    """POST + retry ringan buat 500/503 (model lagi ramai)."""
    for i in range(tries):
        r = requests.post(url, headers=headers, json=body, timeout=180)
        if r.status_code in (500, 503) and i < tries - 1:
            time.sleep(4 * (i + 1))
            continue
        return r
    return r


# ------------------------------------------------------------------ generate
def generate(prompt: str, env: dict, temperature: float = 0.25, max_tokens: int = 16384) -> str:
    """Panggil LLM aktif, minta JSON. Balikin teks mentah (di-parse pemanggil)."""
    c = resolve(env)
    if not c["key"]:
        raise RuntimeError(f"API key kosong buat provider '{c['provider']}'. Isi LLM_API_KEY di .env / menu.")
    if c["openai"]:
        return _gen_openai(prompt, c, temperature, max_tokens)
    return _gen_gemini(prompt, c, temperature, max_tokens)


def _gen_gemini(prompt, c, temperature, max_tokens) -> str:
    url = f"{c['base']}/models/{c['model']}:generateContent?key={c['key']}"
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens,
                                  "responseMimeType": "application/json",
                                  "thinkingConfig": {"thinkingBudget": 0}}}
    r = _post(url, {}, body)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini {r.status_code}: {r.text[:400]}")
    parts = (r.json().get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts)
    if not text:
        raise RuntimeError(f"Respons kosong/diblokir: {r.text[:300]}")
    return text


def _gen_openai(prompt, c, temperature, max_tokens) -> str:
    url = f"{c['base'].rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {c['key']}", "Content-Type": "application/json"}
    body = {"model": c["model"],
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature, "max_tokens": max_tokens,
            "response_format": {"type": "json_object"}}
    r = _post(url, headers, body)
    if r.status_code == 400 and "response_format" in r.text:      # provider tak dukung json mode
        body.pop("response_format", None)
        r = _post(url, headers, body)
    if r.status_code != 200:
        raise RuntimeError(f"{c['label']} {r.status_code}: {r.text[:400]}")
    return (r.json().get("choices") or [{}])[0].get("message", {}).get("content", "") or ""


# ------------------------------------------------------------------ utilitas menu
# model non-chat (suara/gambar/embedding/dll) gak relevan buat analisa -> dibuang dari daftar
_NON_CHAT = ("embed", "tts", "whisper", "audio", "realtime", "transcribe", "image", "moderation", "guard",
             "search", "aqa", "imagen", "veo", "live", "robotics", "computer-use", "dall-e", "davinci",
             "babbage", "sora", "vision")
_SNAPSHOT = re.compile(r"(\d{4}-\d{2}-\d{2}|\d{2}-\d{4}|\d{2}-\d{2})$|-\d{3}$")   # varian bertanggal / -001


def chat_models(provider: str, names: list[str]) -> list[str]:
    """Saring daftar mentah provider -> model chat aja, versi bertanggal dibuang.
    Urutan: model rekomendasi (daftar bawaan) dulu, sisanya terbaru dulu."""
    out = {n for n in names if not any(s in n.lower() for s in _NON_CHAT) and not _SNAPSHOT.search(n)}
    if provider == "openai":
        out = {n for n in out if n.startswith(("gpt-", "o1", "o3", "o4"))}
    elif provider == "gemini":
        out = {n for n in out if n.startswith("gemini-")}
    head = [m for m in PROVIDERS.get(provider, {}).get("models", []) if m in out]
    natural = lambda s: [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]
    return head + sorted(out - set(head), key=natural, reverse=True)


def list_models(env: dict) -> list[str]:
    c = resolve(env)
    try:
        if c["openai"]:
            r = requests.get(f"{c['base'].rstrip('/')}/models",
                             headers={"Authorization": f"Bearer {c['key']}"}, timeout=30)
            return chat_models(c["provider"], [m["id"] for m in r.json().get("data", [])])
        r = requests.get(f"{c['base']}/models?key={c['key']}&pageSize=1000", timeout=30)
        return chat_models(c["provider"], [m["name"].replace("models/", "") for m in r.json().get("models", [])
                                           if "generateContent" in m.get("supportedGenerationMethods", [])])
    except Exception:
        return []


def check_key(env: dict) -> bool | None:
    """Cek API key GRATIS (cuma nanya daftar model, gak nyuruh LLM nulis -> 0 token).
    True = valid, False = ditolak/kosong, None = gak ketahuan (jaringan/server provider)."""
    c = resolve(env)
    if not c["key"]:
        return False
    try:
        auth = {"Authorization": f"Bearer {c['key']}"}
        if c["openai"]:
            r = requests.get(f"{c['base'].rstrip('/')}/models", headers=auth, timeout=15)
        else:
            r = requests.get(f"{c['base']}/models?key={c['key']}&pageSize=1", timeout=15)
    except Exception:
        return None
    if r.status_code == 200:
        return True
    return False if r.status_code in (400, 401, 403) else None


def balance_usd(env: dict) -> float | None:
    """Sisa saldo (USD) — cuma DeepSeek yang nyediain endpoint gratisnya. Lainnya None."""
    c = resolve(env)
    if c["provider"] != "deepseek" or not c["key"]:
        return None
    try:
        r = requests.get("https://api.deepseek.com/user/balance",
                         headers={"Authorization": f"Bearer {c['key']}"}, timeout=15)
        infos = r.json().get("balance_infos") or []
        usd = [b for b in infos if b.get("currency") == "USD"] or infos
        return float(usd[0]["total_balance"]) if usd else None
    except Exception:
        return None


def test_connection(env: dict) -> tuple[bool, str]:
    """Ping kecil: balikin (ok, pesan) buat tombol 'Tes' di menu."""
    c = resolve(env)
    try:
        txt = generate("Balas satu kata JSON: {\"ok\":true}", env, max_tokens=20)
        return True, f"OK — {c['label']} / {c['model']} nyambung."
    except Exception as e:
        return False, f"GAGAL — {str(e)[:200]}"
