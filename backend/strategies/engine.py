"""
Strategy / scoring engine.

For each coin and each scan mode (intraday, swing, btst, range, investment),
this module computes a transparent, rule-based signal: direction, entry,
stop-loss, target1/target2/target3, confidence score, and the indicator
readings that drove the call. Every number is traceable back to a specific
rule -- no black-box ML scoring, consistent with the "beginner indicator
guide" approach already validated with the user (EMA 9/21, RSI 14, VWAP,
Bollinger Bands, MACD, ATR for stop sizing).

Each mode uses a different timeframe and weighting because the holding
period and risk tolerance differ:

  intraday    -> 15m candles, VWAP + EMA9/21 + RSI, same-day exit
  btst        -> 1h candles, momentum continuation into next session
  swing       -> 4h candles, EMA21/50 + MACD + BB squeeze/breakout
  range       -> 1h candles, Bollinger Band mean-reversion inside a channel
  investment  -> 1d candles, long-term trend + structure, wide targets
"""

import indicators as ind

MODES = ["intraday", "btst", "swing", "range", "investment"]

MODE_CONFIG = {
    "intraday": {"interval": "15m", "limit": 100, "label": "Intraday (same-day)"},
    "btst":     {"interval": "1h",  "limit": 100, "label": "BTST (overnight carry)"},
    "swing":    {"interval": "4h",  "limit": 150, "label": "Swing (2-10 days)"},
    "range":    {"interval": "1h",  "limit": 100, "label": "Range (mean-reversion)"},
    "investment": {"interval": "1d", "limit": 200, "label": "Investment (weeks-months)"},
}


def _safe_round(x, n=6):
    return round(x, n) if isinstance(x, (int, float)) else x


def compute_indicator_snapshot(candles):
    """Compute every indicator reading once, shared across all mode strategies."""
    c = ind.closes(candles)
    last_close = c[-1]

    ema9 = ind.ema(c, 9)
    ema21 = ind.ema(c, 21)
    ema50 = ind.ema(c, 50) if len(c) >= 50 else None
    rsi14 = ind.rsi(c, 14)
    macd_line, macd_signal, macd_hist = ind.macd(c, 12, 26, 9)
    bb_upper, bb_mid, bb_lower = ind.bollinger_bands(c, 20, 2)
    atr14 = ind.atr(candles, 14)
    vwap = ind.session_vwap(candles[-min(len(candles), 96):])  # ~last day on intraday TFs
    obv_val, obv_series = ind.obv(candles)
    obv_prev = obv_series[-5] if len(obv_series) >= 5 else obv_val
    swing_high, swing_low = ind.swing_high_low(candles, lookback=20)

    return {
        "last_close": last_close,
        "ema9": ema9,
        "ema21": ema21,
        "ema50": ema50,
        "rsi14": rsi14,
        "macd_line": macd_line,
        "macd_signal": macd_signal,
        "macd_hist": macd_hist,
        "bb_upper": bb_upper,
        "bb_mid": bb_mid,
        "bb_lower": bb_lower,
        "atr14": atr14,
        "vwap": vwap,
        "obv": obv_val,
        "obv_trend_up": obv_val > obv_prev if obv_prev is not None else None,
        "swing_high": swing_high,
        "swing_low": swing_low,
    }


def _direction_and_score(snap, weights):
    """
    Generic bull/bear scoring: each rule contributes +1/-1/0 to a running
    score. weights lets each mode emphasize different signals.
    Returns (direction: 'long'|'short'|'neutral', score: int, reasons: list[str], max_score: int)
    """
    score = 0
    max_score = 0
    reasons = []

    def vote(condition_long, condition_short, weight, label):
        nonlocal score, max_score
        max_score += weight
        if condition_long:
            score += weight
            reasons.append(f"+{label}")
        elif condition_short:
            score -= weight
            reasons.append(f"-{label}")

    ema9, ema21, ema50 = snap["ema9"], snap["ema21"], snap["ema50"]
    rsi14 = snap["rsi14"]
    price = snap["last_close"]
    vwap = snap["vwap"]
    macd_hist = snap["macd_hist"]
    bb_upper, bb_lower = snap["bb_upper"], snap["bb_lower"]
    obv_up = snap["obv_trend_up"]

    if ema9 is not None and ema21 is not None:
        vote(ema9 > ema21, ema9 < ema21, weights.get("ema_cross", 2), "EMA9>21")

    if ema50 is not None and ema21 is not None:
        vote(ema21 > ema50, ema21 < ema50, weights.get("ema_trend", 1), "EMA21>50")

    if rsi14 is not None:
        # momentum confirmation zone, not extreme reversal zone
        vote(50 < rsi14 < 70, 30 < rsi14 < 50, weights.get("rsi", 1), "RSI zone")
        # extreme zones penalize chasing
        vote(False, rsi14 > 75, weights.get("rsi_extreme", 1), "RSI overbought")
        vote(False, rsi14 < 25, weights.get("rsi_extreme", 1), "RSI oversold-bearish")

    if vwap is not None:
        vote(price > vwap, price < vwap, weights.get("vwap", 2), "Price vs VWAP")

    if macd_hist is not None:
        vote(macd_hist > 0, macd_hist < 0, weights.get("macd", 1), "MACD hist")

    if bb_upper is not None and bb_lower is not None:
        # breakout context (used more by swing/intraday)
        vote(price >= bb_upper, price <= bb_lower, weights.get("bb_breakout", 0), "BB breakout")

    if obv_up is not None:
        vote(obv_up, not obv_up, weights.get("obv", 1), "OBV trend")

    if max_score == 0:
        return "neutral", 0, ["insufficient data"], 0

    if score >= max_score * 0.35:
        direction = "long"
    elif score <= -max_score * 0.35:
        direction = "short"
    else:
        direction = "neutral"

    return direction, score, reasons, max_score


def _build_levels_trend(snap, direction, atr_mult_sl=1.5, rr_targets=(1.5, 2.5, 4.0)):
    """
    ATR-anchored entry/SL/targets for trend-following modes
    (intraday/btst/swing/investment). rr_targets are risk-multiples for
    target1/2/3 (e.g. 1.5R, 2.5R, 4R).
    """
    price = snap["last_close"]
    atr14 = snap["atr14"] or (price * 0.01)  # fallback: 1% of price if ATR unavailable

    if direction == "long":
        entry = price
        sl = entry - atr_mult_sl * atr14
        risk = entry - sl
        targets = [entry + r * risk for r in rr_targets]
    elif direction == "short":
        entry = price
        sl = entry + atr_mult_sl * atr14
        risk = sl - entry
        targets = [entry - r * risk for r in rr_targets]
    else:
        return None

    return {
        "entry": _safe_round(entry),
        "stop_loss": _safe_round(sl),
        "target1": _safe_round(targets[0]),
        "target2": _safe_round(targets[1]),
        "target3": _safe_round(targets[2]),
        "risk_per_unit": _safe_round(abs(entry - sl)),
        "rr_targets": list(rr_targets),
    }


def _build_levels_range(snap, direction):
    """
    Mean-reversion levels for the range mode: entry near band edge,
    SL just beyond the band, target back toward the midline / opposite band.

    Important: the signal can fire when price has already poked slightly
    past the band edge (that's the trigger condition), so the stop-loss
    must be anchored relative to the *entry price itself* using an ATR
    buffer -- not purely relative to the band level -- otherwise a fast-
    moving touch can place the band-anchored SL on the wrong side of entry
    (e.g. SL above entry on a long). We take whichever distance is farther
    from entry (band-anchored vs ATR-anchored) so the stop never sits
    uncomfortably tight, but always enforce correct ordering afterward.
    """
    price = snap["last_close"]
    bb_upper, bb_mid, bb_lower = snap["bb_upper"], snap["bb_mid"], snap["bb_lower"]
    atr14 = snap["atr14"] or (price * 0.01)

    if bb_upper is None or bb_lower is None:
        return None

    entry = price

    if direction == "long":
        sl_from_band = bb_lower - 0.5 * atr14
        sl_from_price = entry - 1.0 * atr14
        sl = min(sl_from_band, sl_from_price)  # the lower (further/safer) of the two
        target1 = bb_mid
        target2 = bb_upper
        target3 = bb_upper + 0.5 * atr14
        # enforce correct ordering even in edge cases (e.g. extremely tight bands)
        if sl >= entry:
            sl = entry - 1.0 * atr14
        if target1 <= entry:
            target1 = entry + 1.0 * atr14
        if target2 <= target1:
            target2 = target1 + 1.0 * atr14
        if target3 <= target2:
            target3 = target2 + 0.5 * atr14
    elif direction == "short":
        sl_from_band = bb_upper + 0.5 * atr14
        sl_from_price = entry + 1.0 * atr14
        sl = max(sl_from_band, sl_from_price)  # the higher (further/safer) of the two
        target1 = bb_mid
        target2 = bb_lower
        target3 = bb_lower - 0.5 * atr14
        if sl <= entry:
            sl = entry + 1.0 * atr14
        if target1 >= entry:
            target1 = entry - 1.0 * atr14
        if target2 >= target1:
            target2 = target1 - 1.0 * atr14
        if target3 >= target2:
            target3 = target2 - 0.5 * atr14
    else:
        return None

    return {
        "entry": _safe_round(entry),
        "stop_loss": _safe_round(sl),
        "target1": _safe_round(target1),
        "target2": _safe_round(target2),
        "target3": _safe_round(target3),
        "risk_per_unit": _safe_round(abs(entry - sl)),
        "band_mid": _safe_round(bb_mid),
    }


def scan_intraday(candles):
    snap = compute_indicator_snapshot(candles)
    weights = {"ema_cross": 2, "vwap": 3, "rsi": 1, "rsi_extreme": 1, "macd": 1, "obv": 1}
    direction, score, reasons, max_score = _direction_and_score(snap, weights)
    levels = _build_levels_trend(snap, direction, atr_mult_sl=1.2, rr_targets=(1.2, 2.0, 3.0))
    return _package(snap, direction, score, max_score, reasons, levels, mode="intraday")


def scan_btst(candles):
    snap = compute_indicator_snapshot(candles)
    weights = {"ema_cross": 2, "vwap": 1, "rsi": 1, "macd": 2, "obv": 2}
    direction, score, reasons, max_score = _direction_and_score(snap, weights)
    levels = _build_levels_trend(snap, direction, atr_mult_sl=1.8, rr_targets=(1.5, 2.5, 3.5))
    return _package(snap, direction, score, max_score, reasons, levels, mode="btst")


def scan_swing(candles):
    snap = compute_indicator_snapshot(candles)
    weights = {"ema_cross": 2, "ema_trend": 2, "rsi": 1, "macd": 2, "bb_breakout": 1, "obv": 1}
    direction, score, reasons, max_score = _direction_and_score(snap, weights)
    levels = _build_levels_trend(snap, direction, atr_mult_sl=2.0, rr_targets=(1.5, 3.0, 5.0))
    return _package(snap, direction, score, max_score, reasons, levels, mode="swing")


def _trend_strength(candles, ema_period=21, lookback=10):
    """
    Cheap trend-strength proxy without needing a full ADX implementation:
    measures EMA slope over `lookback` bars as a percentage of price.
    Used to suppress range/mean-reversion signals during strong trends,
    where fading the band edge is fighting the tape rather than reverting.
    Returns a float; > ~0.5% per bar on this scale is a "strong trend".
    """
    c = ind.closes(candles)
    series = ind.ema_series(c, ema_period)
    valid = [v for v in series if v is not None]
    if len(valid) < lookback + 1:
        return 0.0
    recent = valid[-lookback:]
    slope_pct = (recent[-1] - recent[0]) / recent[0] * 100 if recent[0] else 0.0
    return abs(slope_pct)


def scan_range(candles):
    snap = compute_indicator_snapshot(candles)
    price = snap["last_close"]
    bb_upper, bb_lower = snap["bb_upper"], snap["bb_lower"]
    rsi14 = snap["rsi14"]

    # Range mode direction rule is distinct: fade the band edge, not follow trend.
    # Guard: suppress fades when the underlying trend is strong, since buying
    # a "low band touch" inside a strong downtrend is catching a falling knife,
    # not mean reversion.
    direction = "neutral"
    reasons = []
    trend_strength = _trend_strength(candles)
    TREND_SUPPRESS_THRESHOLD = 1.5  # % EMA21 move over lookback window

    if trend_strength >= TREND_SUPPRESS_THRESHOLD:
        reasons.append(
            f"range signals suppressed: trend strength {trend_strength:.2f}% "
            f">= {TREND_SUPPRESS_THRESHOLD}% threshold (avoid fading a strong trend)"
        )
        levels = None
        score = 0
        return _package(snap, direction, score, 1, reasons, levels, mode="range")

    if bb_upper is not None and bb_lower is not None and rsi14 is not None:
        band_width = bb_upper - bb_lower
        if band_width > 0:
            pos_in_band = (price - bb_lower) / band_width  # 0 = lower band, 1 = upper band
            if pos_in_band <= 0.15 and rsi14 < 40:
                direction = "long"
                reasons.append("price near lower band + RSI<40 (fade up)")
            elif pos_in_band >= 0.85 and rsi14 > 60:
                direction = "short"
                reasons.append("price near upper band + RSI>60 (fade down)")
            else:
                reasons.append(f"price mid-band (pos={pos_in_band:.2f}), no edge to fade")

    levels = _build_levels_range(snap, direction)
    score = 1 if direction == "long" else (-1 if direction == "short" else 0)
    return _package(snap, direction, score, 1, reasons, levels, mode="range")


def scan_investment(candles):
    snap = compute_indicator_snapshot(candles)
    weights = {"ema_cross": 2, "ema_trend": 3, "rsi": 1, "macd": 2, "obv": 2}
    direction, score, reasons, max_score = _direction_and_score(snap, weights)
    # investment mode never shorts in this build -- it's a long-only
    # accumulation framework, consistent with "investment" rather than
    # leveraged derivatives use.
    if direction == "short":
        direction = "neutral"
        reasons.append("short signals suppressed in investment mode (long-only)")
    levels = _build_levels_trend(snap, direction, atr_mult_sl=3.0, rr_targets=(2.0, 4.0, 7.0))
    return _package(snap, direction, score, max_score, reasons, levels, mode="investment")


SCANNERS = {
    "intraday": scan_intraday,
    "btst": scan_btst,
    "swing": scan_swing,
    "range": scan_range,
    "investment": scan_investment,
}


def _package(snap, direction, score, max_score, reasons, levels, mode):
    confidence = 0
    if max_score and direction != "neutral":
        confidence = round(min(abs(score) / max_score, 1.0) * 100)

    return {
        "mode": mode,
        "direction": direction,        # 'long' | 'short' | 'neutral'
        "confidence_pct": confidence,
        "score": score,
        "max_score": max_score,
        "reasons": reasons,
        "levels": levels,              # entry/SL/targets, or None if neutral
        "indicators": {
            "close": _safe_round(snap["last_close"]),
            "ema9": _safe_round(snap["ema9"]),
            "ema21": _safe_round(snap["ema21"]),
            "ema50": _safe_round(snap["ema50"]),
            "rsi14": _safe_round(snap["rsi14"], 2),
            "macd_hist": _safe_round(snap["macd_hist"], 6),
            "vwap": _safe_round(snap["vwap"]),
            "bb_upper": _safe_round(snap["bb_upper"]),
            "bb_mid": _safe_round(snap["bb_mid"]),
            "bb_lower": _safe_round(snap["bb_lower"]),
            "atr14": _safe_round(snap["atr14"]),
        },
    }


def quick_signal(candles):
    """
    Lightweight single-timeframe signal for contexts (like the heatmap)
    that already have one batch of candles and just want a direction +
    confidence overlay, without needing run_scan's mode->interval lookup.
    Reuses the same scoring rules as scan_intraday.
    """
    if not candles or len(candles) < 25:
        return {"direction": None, "confidence_pct": None}
    snap = compute_indicator_snapshot(candles)
    weights = {"ema_cross": 2, "vwap": 3, "rsi": 1, "rsi_extreme": 1, "macd": 1, "obv": 1}
    direction, score, reasons, max_score = _direction_and_score(snap, weights)
    confidence = round(min(abs(score) / max_score, 1.0) * 100) if max_score and direction != "neutral" else 0
    return {"direction": direction, "confidence_pct": confidence}


def run_scan(symbol, candles_by_interval, modes=None):
    """
    candles_by_interval: dict like {"15m": [...], "1h": [...], "4h": [...], "1d": [...]}
    Caller (the API layer) is responsible for fetching the right interval
    per mode via the price waterfall and passing them in here.
    """
    modes = modes or MODES
    out = {}
    for mode in modes:
        interval = MODE_CONFIG[mode]["interval"]
        candles = candles_by_interval.get(interval)
        if not candles or len(candles) < 25:
            out[mode] = {"mode": mode, "direction": "neutral", "error": "insufficient candle history"}
            continue
        out[mode] = SCANNERS[mode](candles)
    return {"symbol": symbol, "results": out}
