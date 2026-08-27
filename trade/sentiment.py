"""Mesin sentimen — dibikin SWAPPABLE.

Semua scorer implement interface `SentimentScorer` (punya .score(text) -> dict).
Baseline sekarang: `LexiconScorer` (kamus kata bilingual EN+ID, tanpa dep berat).
Upgrade nanti: FinBERT (EN) / IndoBERT (ID) / Ollama — tinggal bikin kelas baru
dengan interface yang sama, terus diadu di backtest mana yang paling akur.
"""
from __future__ import annotations

import re

# ------------------------------------------------------------------ kamus
# Kata tunggal (dicek per-token)
_POS_WORDS = {
    # EN
    "beat", "beats", "surge", "surged", "surges", "jump", "jumped", "jumps",
    "rally", "rallies", "upgrade", "upgraded", "outperform", "outperforms",
    "record", "profit", "profits", "growth", "soar", "soared", "soars",
    "gain", "gains", "strong", "stronger", "bullish", "raise", "raises", "raised",
    "tops", "topped", "higher", "expand", "expands", "win", "wins", "won",
    "undervalued", "rebound", "rebounds", "boost", "boosts", "rise", "rises", "rose",
    "climb", "climbs", "climbed", "advance", "advances", "positive", "optimistic",
    "surpass", "surpasses", "exceeds", "exceeded", "upbeat", "momentum", "breakout",
    # ID
    "naik", "menguat", "melonjak", "lonjak", "untung", "laba", "cuan", "tumbuh",
    "pertumbuhan", "positif", "rekor", "moncer", "borong", "akumulasi", "ekspansi",
    "meroket", "melesat", "menanjak", "kenaikan", "meningkat", "optimis", "prospek",
    "dividen", "surplus", "menguatnya", "melejit",
}
_NEG_WORDS = {
    # EN
    "miss", "missed", "misses", "plunge", "plunged", "fall", "fell", "falls",
    "drop", "dropped", "drops", "downgrade", "downgraded", "cut", "cuts",
    "loss", "losses", "weak", "weaker", "bearish", "warn", "warns", "warned",
    "slump", "slumped", "decline", "declines", "declined", "lawsuit", "fraud",
    "halt", "halted", "tumble", "tumbled", "sink", "sinks", "crash", "crashes",
    "plummet", "plummets", "slide", "slides", "negative", "concerns", "risk", "risks",
    "investigation", "probe", "bankruptcy", "default", "recall", "slowdown", "lower",
    # ID
    "turun", "anjlok", "merosot", "rugi", "kerugian", "melemah", "tekanan",
    "tertekan", "koreksi", "terkoreksi", "jatuh", "ambruk", "negatif", "memburuk",
    "penurunan", "pesimis", "gagal", "jeblok", "longsor", "amblas", "terpuruk",
    "melemahnya", "anjloknya",
}

# Frasa (dicek sebagai substring, boleh multi-kata) — lebih spesifik, bobotnya sama
_POS_PHRASES = [
    "net buy", "buy rating", "rekomendasi beli", "net buy asing", "target naik",
    "cetak laba", "kinerja positif", "record high", "all-time high",
    "beat estimates", "above estimates", "raised guidance", "price target raised",
]
_NEG_PHRASES = [
    "net sell", "sell rating", "rekomendasi jual", "net sell asing",
    "below estimates", "miss estimates", "profit warning", "rugi bersih",
    "kinerja negatif", "cut guidance", "price target cut", "auto reject bawah",
]

_TOKEN_RE = re.compile(r"[a-zA-Z]+")
_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str | None) -> str:
    return _TAG_RE.sub(" ", text or "")


class SentimentScorer:
    """Interface. Semua scorer wajib punya .score(text) -> dict."""
    name = "base"

    def score(self, text: str) -> dict:
        raise NotImplementedError

    def score_many(self, texts):
        return [self.score(t) for t in texts]


class LexiconScorer(SentimentScorer):
    """Baseline: hitung kata positif vs negatif. Skor = (pos-neg)/(pos+neg) di [-1,1]."""
    name = "lexicon"

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold

    def score(self, text: str) -> dict:
        low = strip_html(text).lower()
        tokens = _TOKEN_RE.findall(low)

        pos = sum(1 for w in tokens if w in _POS_WORDS)
        neg = sum(1 for w in tokens if w in _NEG_WORDS)
        pos += sum(low.count(p) for p in _POS_PHRASES)
        neg += sum(low.count(p) for p in _NEG_PHRASES)

        total = pos + neg
        score = (pos - neg) / total if total else 0.0
        if score > self.threshold:
            label = "positive"
        elif score < -self.threshold:
            label = "negative"
        else:
            label = "neutral"
        return {"label": label, "score": round(score, 3),
                "pos": pos, "neg": neg, "scorer": self.name}
