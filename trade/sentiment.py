"""Sentimen berita = LEXICON (kamus kata/frasa bursa, EN+ID). Skor (pos-neg)/(pos+neg) di [-1, 1].

Kenapa bukan model NLP (BERT): udah dites Agu 2026 dan KALAH buat judul saham IDX —
`w11wo/indonesian-roberta-base-sentiment-classifier` cenderung netral semua, dan
`michaelmanurung/finbert-indonesia` malah baca 'Asing Borong BBCA' 95% NEGATIF.
Sentimen finansial (bullish/bearish) beda sama sentimen bahasa; kamus yang paham istilah
bursa (borong / net sell / anjlok) justru lebih akur. Jangan diulang tanpa model finansial-ID baru.
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
    "dividen", "surplus", "menguatnya", "melejit", "akuisisi", "buyback",
    # + istilah bursa (pertajam lexicon pasca-eksperimen BERT)
    "reli", "terbang", "melambung", "diborong", "diakumulasi", "cemerlang",
    "kinclong", "menghijau", "loncat", "gainers", "menggeliat",
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
    "melemahnya", "anjloknya", "suspensi", "disuspensi", "pailit", "pkpu",
    "delisting", "penundaan", "gugatan",
    # + istilah bursa
    "tergerus", "ambles", "ambrol", "tumbang", "lesu", "loyo", "memerah",
    "menukik", "tersungkur", "terkapar", "lego",
}

# Frasa (dicek sebagai substring, boleh multi-kata) — lebih spesifik, bobotnya sama
_POS_PHRASES = [
    "net buy", "buy rating", "rekomendasi beli", "net buy asing", "target naik",
    "cetak laba", "kinerja positif", "record high", "all-time high",
    "beat estimates", "above estimates", "raised guidance", "price target raised",
    "pembagian dividen", "tender offer", "stock split", "buy back",
    # + frasa bursa
    "auto reject atas", "asing borong", "diborong asing", "asing masuk",
    "net foreign buy", "akumulasi asing", "top gainers", "zona hijau", "naik kelas",
    "tebar dividen", "bagi dividen", "potensi cuan", "berpotensi menguat",
    "target dinaikkan", "menaikkan target", "prospek cerah", "kinerja cemerlang",
    "raih laba", "cetak rekor", "rekomendasi akumulasi",
]
_NEG_PHRASES = [
    "net sell", "sell rating", "rekomendasi jual", "net sell asing",
    "below estimates", "miss estimates", "profit warning", "rugi bersih",
    "kinerja negatif", "cut guidance", "price target cut", "auto reject bawah",
    "permintaan penjelasan", "unusual market activity", "gagal bayar", "penjelasan bursa",
    # + frasa bursa
    "asing jual", "asing lego", "dilepas asing", "asing keluar", "net foreign sell",
    "top losers", "zona merah", "pemantauan khusus", "profit taking", "tekanan jual",
    "aksi jual", "laba turun", "laba anjlok", "laba merosot", "laba susut",
    "kas susut", "kas menyusut", "arus kas negatif", "rugi membengkak",
    "kinerja lesu", "terjun bebas", "wanprestasi", "restrukturisasi utang",
    "laba bersih turun", "laba bersih anjlok", "laba bersih merosot",
    "laba bersih susut", "laba bersih tergerus", "malah susut", "malah turun",
]

_TOKEN_RE = re.compile(r"[a-zA-Z]+")
_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text: str | None) -> str:
    return _TAG_RE.sub(" ", text or "")


class LexiconScorer:
    """Hitung kata/frasa positif vs negatif di judul + ringkasan berita."""
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
