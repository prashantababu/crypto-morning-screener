"""
Heatmap aggregation.

Builds the data structure consumed by the frontend's heatmap grid: one cell
per coin, sized/colored by a chosen metric (24h % change, volume, or signal
confidence from the strategy engine), grouped by category for layout.
"""

from coin_universe import COIN_UNIVERSE, symbol_meta
import indicators as ind


def pct_change_24h(candles_1h):
    """Approximate 24h % change using the last 24 hourly candles."""
    if not candles_1h or len(candles_1h) < 25:
        return None
    now = candles_1h[-1]["close"]
    then = candles_1h[-25]["close"]
    return ind.pct_change(then, now)


def volume_24h(candles_1h):
    if not candles_1h or len(candles_1h) < 24:
        return None
    return sum(c["volume"] for c in candles_1h[-24:])


def build_heatmap(symbol_candles_1h, scan_results_by_symbol=None):
    """
    symbol_candles_1h: {symbol: [candles...]}  (1h interval, >=25 bars)
    scan_results_by_symbol: optional {symbol: {"direction":..., "confidence_pct":...}}
        (output of engine.quick_signal) to overlay signal direction/confidence
        on each heatmap cell.

    Returns: {category: [ {symbol, name, change_24h_pct, volume_24h,
                           signal_direction, signal_confidence}, ... ] }
    """
    scan_results_by_symbol = scan_results_by_symbol or {}
    heatmap = {}

    for category, coins in COIN_UNIVERSE.items():
        cells = []
        for coin in coins:
            symbol = coin["symbol"]
            candles = symbol_candles_1h.get(symbol)
            if not candles:
                cells.append({
                    "symbol": symbol, "name": coin["name"],
                    "change_24h_pct": None, "volume_24h": None,
                    "signal_direction": None, "signal_confidence": None,
                    "error": "no data",
                })
                continue

            change = pct_change_24h(candles)
            vol = volume_24h(candles)

            signal_direction, signal_confidence = None, None
            quick = scan_results_by_symbol.get(symbol)
            if quick:
                signal_direction = quick.get("direction")
                signal_confidence = quick.get("confidence_pct")

            cells.append({
                "symbol": symbol,
                "name": coin["name"],
                "change_24h_pct": round(change, 2) if change is not None else None,
                "volume_24h": round(vol, 2) if vol is not None else None,
                "signal_direction": signal_direction,
                "signal_confidence": signal_confidence,
                "options_available": coin["options"],
            })
        # sort by absolute change descending so biggest movers stand out
        cells.sort(key=lambda x: abs(x["change_24h_pct"]) if x["change_24h_pct"] is not None else -1, reverse=True)
        heatmap[category] = cells

    return heatmap
