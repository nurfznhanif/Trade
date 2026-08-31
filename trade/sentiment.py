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


class IndoBertScorer(SentimentScorer):
    """Scorer transformer (OPSIONAL, EKSPERIMENTAL) — interface swappable buat model NLP.

    ⚠️ HASIL TES (Agu 2026): model Indonesia off-the-shelf yang dites JUSTRU KALAH dari
    lexicon buat JUDUL berita saham:
      - umum `w11wo/indonesian-roberta-base-sentiment-classifier` → cenderung 'neutral'
        semua (mis. 'Asing Borong BBCA' & 'IHSG Anjlok' dua-duanya dibaca netral);
      - keuangan `michaelmanurung/finbert-indonesia` → malah keliru ('Asing Borong BBCA'
        di-skor 95% NEGATIF).
    Sebabnya: sentimen FINANSIAL (bullish/bearish) beda dari sentimen LINGUISTIK (emosi
    kalimat). Lexicon 'bodoh' menang karena kamusnya paham istilah saham (borong/net sell/
    anjlok). Jadi kelas ini BUKAN default — disimpen sebagai infrastruktur kalau nanti ada
    model finance-Indonesia yang lebih akur (tinggal `IndoBertScorer(model="...")`).

    Butuh `pip install torch transformers` (~GB). Skor dipetakan ke [-1,1] =
    P(positif) − P(negatif). torch/transformers di-import DI DALAM __init__ biar
    `LexiconScorer` tetap jalan tanpa dep berat itu.
    """
    name = "indobert"
    DEFAULT_MODEL = "w11wo/indonesian-roberta-base-sentiment-classifier"

    def __init__(self, model: str | None = None, batch_size: int = 32,
                 max_length: int = 256):
        from transformers import pipeline          # import berat — sengaja lokal
        try:
            import torch
            device = 0 if torch.cuda.is_available() else -1
        except Exception:
            device = -1
        self.batch_size = batch_size
        self.max_length = max_length
        self.model_id = model or self.DEFAULT_MODEL
        self.pipe = pipeline("sentiment-analysis", model=self.model_id, device=device)

    @staticmethod
    def _to_signed(scores: list) -> dict:
        """scores: list of {label, score} (semua kelas). -> skema {label,score,pos,neg,scorer}."""
        d = {str(s["label"]).lower(): float(s["score"]) for s in scores}
        pos = d.get("positive", d.get("positif", d.get("label_2", 0.0)))
        neg = d.get("negative", d.get("negatif", d.get("label_0", 0.0)))
        neu = d.get("neutral", d.get("netral", d.get("label_1", 0.0)))
        score = round(pos - neg, 3)
        label = max((("positive", pos), ("neutral", neu), ("negative", neg)),
                    key=lambda x: x[1])[0]
        return {"label": label, "score": score,
                "pos": round(pos, 3), "neg": round(neg, 3), "scorer": "indobert"}

    def score(self, text: str) -> dict:
        out = self.pipe(strip_html(text) or "-", top_k=None,
                        truncation=True, max_length=self.max_length)
        if out and isinstance(out[0], list):       # kadang dibungkus 1 lapis
            out = out[0]
        return self._to_signed(out)

    def score_many(self, texts):
        clean = [strip_html(t) or "-" for t in texts]
        res = self.pipe(clean, batch_size=self.batch_size, top_k=None,
                        truncation=True, max_length=self.max_length)
        return [self._to_signed(r if isinstance(r, list) else [r]) for r in res]


def get_scorer(name: str = "lexicon", **kw) -> SentimentScorer:
    """Pilih scorer by name. 'lexicon' (default, ringan) atau 'indobert' (NLP, dep berat)."""
    key = (name or "lexicon").lower()
    if key in ("indobert", "bert", "nlp", "roberta"):
        return IndoBertScorer(**kw)
    if key == "lexicon":
        return LexiconScorer(**kw)
    raise ValueError(f"scorer tak dikenal: {name!r} (pilih: lexicon / indobert)")
