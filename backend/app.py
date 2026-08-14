"""
Crypto Morning Screener - Flask API.

Endpoints:
  GET /api/health
  GET /api/scan?symbol=BTCUSDT&modes=intraday,swing
  GET /api/scan/universe?modes=intraday          -> scans full 45-coin watchlist
  GET /api/heatmap                                -> heatmap grid data
  GET /api/coins                                  -> coin universe metadata

Caching: simple in-memory TTL cache keyed by (symbol, interval). This is
intentionally swappable for Redis later (same pattern as the F&O Morning
Screener) -- see CacheBackend below; swap InMemoryCache for a RedisCache
that implements the same get/set interface when deploying to Render.

Run locally:
    pip install flask flask-cors requests --break-system-packages
    python backend/app.py
Then the dashboard (frontend/index.html) can call http://localhost:5000/api/...
"""

import os
import sys
import time
import logging
from flask import Flask, jsonify, request
from flask_cors import CORS
from smc_engine import run_smc_scan
# Make sibling subpackages importable with flat module names (sources.*,
# strategies.*) regardless of the working directory this is launched from.
_HERE = os.path.dirname(os.path.abspath(__file__))
for _sub in ("sources", "strategies"):
    _path = os.path.join(_HERE, _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from coin_universe import COIN_UNIVERSE, all_symbols, symbol_meta
from price_waterfall import fetch_universe_klines, get_klines_with_fallback, SourceError
from engine import run_scan, quick_signal, MODE_CONFIG, MODES
from heatmap import build_heatmap

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("crypto_screener_api")

app = Flask(__name__)
# CORS_ALLOWED_ORIGINS env var: comma-separated list of allowed origins for
# production (e.g. your deployed dashboard's URL or a custom domain). Left
# unset, this defaults to "*" (allow all) which is fine for local dev and
# for a read-only public market-data API like this one, but tighten it if
# you deploy the dashboard to a known fixed origin.
_cors_origins = os.environ.get("CORS_ALLOWED_ORIGINS", "*")
CORS(app, origins=_cors_origins.split(",") if _cors_origins != "*" else "*")


# ---------------------------------------------------------------------------
# Cache layer (swap for Redis in production -- see docstring)
# ---------------------------------------------------------------------------
class InMemoryCache:
    def __init__(self):
        self._store = {}

    def get(self, key):
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key, value, ttl_seconds):
        self._store[key] = (value, time.time() + ttl_seconds)


cache = InMemoryCache()

# Cache TTLs tuned per interval -- no point refetching 1d candles every 30s.
TTL_BY_INTERVAL = {"15m": 45, "1h": 120, "4h": 300, "1d": 900}


def cached_klines(symbol, interval, limit):
    key = f"{symbol}:{interval}:{limit}"
    hit = cache.get(key)
    if hit is not None:
        return hit, True
    candles, source = get_klines_with_fallback(symbol, interval=interval, limit=limit)
    cache.set(key, (candles, source), TTL_BY_INTERVAL.get(interval, 60))
    return (candles, source), False


def get_candles_by_interval_for_modes(symbol, modes):
    """Fetch (with cache) only the intervals actually needed by requested modes."""
    needed_intervals = {MODE_CONFIG[m]["interval"]: MODE_CONFIG[m]["limit"] for m in modes}
    candles_by_interval = {}
    sources_used = {}
    for interval, limit in needed_intervals.items():
        try:
            (candles, source), from_cache = cached_klines(symbol, interval, limit)
            candles_by_interval[interval] = candles
            sources_used[interval] = {"source": source, "cached": from_cache}
        except SourceError as e:
            logger.warning(f"{symbol} {interval}: {e}")
            candles_by_interval[interval] = None
            sources_used[interval] = {"source": None, "error": str(e)}
    return candles_by_interval, sources_used


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "time": time.time()})


@app.route("/api/coins")
def coins():
    return jsonify(COIN_UNIVERSE)


@app.route("/api/scan")
def scan_one():
    symbol = request.args.get("symbol", "").upper()
    if not symbol:
        return jsonify({"error": "symbol query param required"}), 400

    modes_param = request.args.get("modes")
    modes = modes_param.split(",") if modes_param else MODES
    invalid = [m for m in modes if m not in MODES]
    if invalid:
        return jsonify({"error": f"invalid modes: {invalid}", "valid_modes": MODES}), 400

    candles_by_interval, sources_used = get_candles_by_interval_for_modes(symbol, modes)
    result = run_scan(symbol, candles_by_interval, modes=modes)
    result["data_sources"] = sources_used
    result["meta"] = symbol_meta(symbol)
    return jsonify(result)


@app.route("/api/scan/universe")
def scan_universe():
    modes_param = request.args.get("modes")
    modes = modes_param.split(",") if modes_param else ["intraday"]
    invalid = [m for m in modes if m not in MODES]
    if invalid:
        return jsonify({"error": f"invalid modes: {invalid}", "valid_modes": MODES}), 400

    symbols = all_symbols()
    needed_intervals = {MODE_CONFIG[m]["interval"]: MODE_CONFIG[m]["limit"] for m in modes}

    # Fetch each required interval for the whole universe in parallel (one
    # waterfall pass per interval), then run the strategy engine per symbol.
    interval_data = {}
    for interval, limit in needed_intervals.items():
        interval_data[interval] = fetch_universe_klines(symbols, interval=interval, limit=limit)

    results = {}
    for symbol in symbols:
        candles_by_interval = {}
        for interval in needed_intervals:
            payload = interval_data[interval].get(symbol, {})
            candles_by_interval[interval] = payload.get("candles")
        results[symbol] = run_scan(symbol, candles_by_interval, modes=modes)

    return jsonify({"modes": modes, "results": results, "count": len(symbols)})


@app.route("/api/heatmap")
def heatmap():
    symbols = all_symbols()
    # Limit to 20 candles for heatmap — only needs 24h change + quick signal,
    # not deep history. Keeps the fetch fast on Render free tier.
    raw = fetch_universe_klines(symbols, interval="1h", limit=20)
    symbol_candles = {s: payload.get("candles") for s, payload in raw.items() if payload.get("candles")}

    # Overlay a quick intraday-style signal per coin using the same 1h
    # candles already fetched for the heatmap (avoids a second network
    # round-trip just to color/badge each cell with direction+confidence).
    scan_results = {}
    for symbol, candles in symbol_candles.items():
        if candles and len(candles) >= 15:
            try:
                scan_results[symbol] = quick_signal(candles)
            except Exception as e:
                logger.warning(f"quick_signal failed for {symbol}: {e}")

    data = build_heatmap(symbol_candles, scan_results_by_symbol=scan_results)
    return jsonify(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
