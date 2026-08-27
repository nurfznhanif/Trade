"""Signal engine — gabung teknikal + sentimen jadi keputusan BUY/HOLD/SELL.

Logikanya SENGAJA transparan (skor + daftar alasan), bukan black box, biar:
  (a) gampang diaudit & dipercaya buat duit beneran,
  (b) gampang disetel & diadu di backtest.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SignalParams:
    buy_th: float = 1.5          # skor >= ini -> BUY
    sell_th: float = -1.5        # skor <= ini -> SELL
    rsi_overbought: float = 72.0
    rsi_oversold: float = 30.0
    atr_stop_mult: float = 2.0   # stop = close - 2*ATR
    reward_risk: float = 2.0     # target = close + 2x risiko


def decide(f: dict, p: SignalParams | None = None) -> dict:
    """f: fitur {close, ma20, ma50, rsi, atr, sent, n_news}. Balikin dict sinyal."""
    p = p or SignalParams()
    reasons: list[str] = []
    score = 0.0

    close = f["close"]
    ma20, ma50, rsi_v, atr_v = f.get("ma20"), f.get("ma50"), f.get("rsi"), f.get("atr")
    sent = f.get("sent") or 0.0
    n_news = f.get("n_news") or 0

    # --- Tren (teknikal) ---
    trend_up = ma20 is not None and ma50 is not None and close > ma20 > ma50
    trend_down = ma20 is not None and ma50 is not None and close < ma20 < ma50
    if trend_up:
        score += 1.5
        reasons.append("uptrend (harga>MA20>MA50)")
    elif trend_down:
        score -= 1.5
        reasons.append("downtrend (harga<MA20<MA50)")

    # --- Sentimen berita (dibobot confidence: makin banyak berita, makin dipercaya) ---
    if n_news >= 1:
        conf = min(n_news, 3) / 3.0       # 1 berita=0.33, 2=0.67, >=3=1.0
        score += sent * conf              # sent di [-1,1]
        reasons.append(f"sentimen {sent:+.2f}×{conf:.2f} ({n_news} berita)")

    # --- RSI (jangan ngejar yang overbought; hargai bounce dari oversold) ---
    if rsi_v is not None:
        if rsi_v > p.rsi_overbought:
            score -= 1.0
            reasons.append(f"RSI {rsi_v:.0f} overbought (jangan dikejar)")
        elif rsi_v < p.rsi_oversold and not trend_down:
            score += 0.5
            reasons.append(f"RSI {rsi_v:.0f} oversold (potensi bounce)")

    # --- Keputusan ---
    if score >= p.buy_th:
        action = "BUY"
    elif score <= p.sell_th:
        action = "SELL"
    else:
        action = "HOLD"

    # --- Level risiko (cuma buat BUY) ---
    stop = target = None
    if action == "BUY" and atr_v:
        stop = round(close - p.atr_stop_mult * atr_v, 4)
        risk = close - stop
        if risk > 0:
            target = round(close + p.reward_risk * risk, 4)

    return {"action": action, "score": round(score, 2),
            "stop": stop, "target": target, "reasons": reasons}
