"""
Technical indicators used by the strategy engine.
Pure functions over OHLCV candle lists (no pandas dependency, so this
runs anywhere your Flask backend runs without extra wheel installs).

Candle shape expected: {"open_time", "open", "high", "low", "close", "volume"}
"""

import math


def closes(candles):
    return [c["close"] for c in candles]


def highs(candles):
    return [c["high"] for c in candles]


def lows(candles):
    return [c["low"] for c in candles]


def volumes(candles):
    return [c["volume"] for c in candles]


def ema_series(values, period):
    """Returns EMA series (same length as input, first `period-1` values are None)."""
    if len(values) < period:
        return [None] * len(values)
    k = 2 / (period + 1)
    out = [None] * (period - 1)
    sma = sum(values[:period]) / period
    out.append(sma)
    prev = sma
    for v in values[period:]:
        ema = v * k + prev * (1 - k)
        out.append(ema)
        prev = ema
    return out


def ema(values, period):
    series = ema_series(values, period)
    return series[-1] if series else None


def rsi(values, period=14):
    """Wilder's RSI. Returns last value, or None if insufficient data."""
    if len(values) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(values)):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_gain == 0 and avg_loss == 0:
        return 50.0  # no movement at all -> neutral, not pegged overbought
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def macd(values, fast=12, slow=26, signal=9):
    """Returns (macd_line, signal_line, histogram) for the latest bar."""
    if len(values) < slow + signal:
        return None, None, None
    fast_series = ema_series(values, fast)
    slow_series = ema_series(values, slow)
    macd_line_series = []
    for f, s in zip(fast_series, slow_series):
        if f is None or s is None:
            macd_line_series.append(None)
        else:
            macd_line_series.append(f - s)

    valid = [m for m in macd_line_series if m is not None]
    if len(valid) < signal:
        return None, None, None
    signal_series = ema_series(valid, signal)
    macd_val = valid[-1]
    signal_val = signal_series[-1]
    if signal_val is None:
        return macd_val, None, None
    return macd_val, signal_val, macd_val - signal_val


def bollinger_bands(values, period=20, num_std=2):
    """Returns (upper, mid, lower) for the latest bar."""
    if len(values) < period:
        return None, None, None
    window = values[-period:]
    mid = sum(window) / period
    variance = sum((v - mid) ** 2 for v in window) / period
    std = math.sqrt(variance)
    return mid + num_std * std, mid, mid - num_std * std


def atr(candles, period=14):
    """Average True Range — used for volatility-scaled stop-loss distance."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h, l, prev_close = candles[i]["high"], candles[i]["low"], candles[i - 1]["close"]
        tr = max(h - l, abs(h - prev_close), abs(l - prev_close))
        trs.append(tr)
    if len(trs) < period:
        return None
    # Wilder smoothing
    avg = sum(trs[:period]) / period
    for t in trs[period:]:
        avg = (avg * (period - 1) + t) / period
    return avg


def session_vwap(candles):
    """
    Simple session VWAP over the provided candle window (treats the whole
    window as one session — caller should pass only today's intraday candles
    for a true daily VWAP anchor).
    """
    cum_pv = 0.0
    cum_vol = 0.0
    for c in candles:
        typical_price = (c["high"] + c["low"] + c["close"]) / 3
        cum_pv += typical_price * c["volume"]
        cum_vol += c["volume"]
    if cum_vol == 0:
        return None
    return cum_pv / cum_vol


def obv(candles):
    """On-Balance Volume series; returns last value and series for trend check."""
    if not candles:
        return 0.0, []
    series = [0.0]
    for i in range(1, len(candles)):
        prev_close = candles[i - 1]["close"]
        close = candles[i]["close"]
        vol = candles[i]["volume"]
        if close > prev_close:
            series.append(series[-1] + vol)
        elif close < prev_close:
            series.append(series[-1] - vol)
        else:
            series.append(series[-1])
    return series[-1], series


def swing_high_low(candles, lookback=20):
    """Recent swing high/low over the lookback window — used for SL/target anchoring."""
    window = candles[-lookback:] if len(candles) >= lookback else candles
    return max(c["high"] for c in window), min(c["low"] for c in window)


def pct_change(a, b):
    if a == 0:
        return 0.0
    return (b - a) / a * 100
