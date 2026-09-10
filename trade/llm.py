"""llm.py — lapisan LLM BONGKAR-PASANG. Gak terpaku ke Gemini.

Dua bentuk API yang menutupi hampir semua provider:
  - "gemini"          : Google Generative Language REST
  - OpenAI-compatible : /chat/completions  (DeepSeek, OpenAI, Groq, OpenRouter, Ollama, custom)

Config dibaca dari env (diisi lewat .env / menu dashboard):
  LLM_PROVIDER  gemini | deepseek | openai | groq | openrouter | ollama | custom
  LLM_MODEL     nama model
  LLM_API_KEY   API key (buat gemini boleh fallback ke GEMINI_API_KEY)
  LLM_BASE_URL  override base URL (wajib buat 'custom')
"""
from __future__ import annotations

import time

import requests

# preset tiap provider: label, OpenAI-compatible?, base URL, tempat ambil key, contoh model
PROVIDERS: dict[str, dict] = {
    "gemini": {"label": "Google Gemini", "openai": False,
               "base": "https://generativelanguage.googleapis.com/v1beta",
               "key_url": "aistudio.google.com/apikey",
               "models": ["gemini-3.5-flash", "gemini-flash-lite-latest", "gemini-3.6-flash"]},
    "deepseek": {"label": "DeepSeek", "openai": True, "base": "https://api.deepseek.com",
                 "key_url": "platform.deepseek.com", "models": ["deepseek-chat", "deepseek-reasoner"]},
    "openai": {"label": "OpenAI", "openai": True, "base": "https://api.openai.com/v1",
               "key_url": "platform.openai.com/api-keys", "models": ["gpt-4o-mini", "gpt-4o"]},
    "groq": {"label": "Groq", "openai": True, "base": "https://api.groq.com/openai/v1",
             "key_url": "console.groq.com/keys", "models": ["llama-3.3-70b-versatile", "openai/gpt-oss-120b"]},
    "openrouter": {"label": "OpenRouter", "openai": True, "base": "https://openrouter.ai/api/v1",
                   "key_url": "openrouter.ai/keys", "models": ["deepseek/deepseek-chat", "google/gemini-2.0-flash-exp:free"]},
    "ollama": {"label": "Ollama (lokal, gratis)", "openai": True, "base": "http://localhost:11434/v1",
               "key_url": "-", "models": ["llama3.1", "qwen2.5"]},
    "custom": {"label": "Custom (OpenAI-compatible)", "openai": True, "base": "",
               "key_url": "-", "models": []},
}


def resolve(env: dict) -> dict:
    """Config efektif dari env -> {provider, openai, base, key, model, label}."""
    provider = (env.get("LLM_PROVIDER") or "gemini").strip().lower()
    p = PROVIDERS.get(provider, PROVIDERS["gemini"])
    key = (env.get("LLM_API_KEY") or "").strip()
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
    if not c["key"] and c["provider"] != "ollama":
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
    headers = {"Authorization": f"Bearer {c['key'] or 'ollama'}", "Content-Type": "application/json"}
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
def list_models(env: dict) -> list[str]:
    c = resolve(env)
    try:
        if c["openai"]:
            r = requests.get(f"{c['base'].rstrip('/')}/models",
                             headers={"Authorization": f"Bearer {c['key'] or 'ollama'}"}, timeout=30)
            return sorted(m["id"] for m in r.json().get("data", []))
        r = requests.get(f"{c['base']}/models?key={c['key']}", timeout=30)
        return sorted(m["name"].replace("models/", "") for m in r.json().get("models", [])
                      if "generateContent" in m.get("supportedGenerationMethods", []))
    except Exception:
        return []


def test_connection(env: dict) -> tuple[bool, str]:
    """Ping kecil: balikin (ok, pesan) buat tombol 'Tes' di menu."""
    c = resolve(env)
    try:
        txt = generate("Balas satu kata JSON: {\"ok\":true}", env, max_tokens=20)
        return True, f"OK — {c['label']} / {c['model']} nyambung."
    except Exception as e:
        return False, f"GAGAL — {str(e)[:200]}"
