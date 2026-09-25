"""
Crypto Morning Screener - Flask API.

Endpoints:
  GET /api/health
  GET /api/scan?symbol=BTCUSD&modes=intraday,swing
  GET /api/scan/universe?modes=intraday          -> scans full 118-coin universe
  GET /api/scan/smc                              -> Smart Money Concepts scan (top 20 by confidence)
  GET /api/scan/breakout                         -> Breakout + Retest scan (30 priority coins)
  GET /api/heatmap                               -> heatmap grid data
  GET /api/coins                                 -> coin universe metadata

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
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, jsonify, request
from flask_cors import CORS

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

# Optional engines — imported with fallback so the app still starts if a file
# is missing (helpful during incremental deploys).
try:
    from smc_engine import run_smc_scan
    _HAS_SMC = True
except ImportError:
    _HAS_SMC = False

try:
    from breakout_engine import run_breakout_scan
    _HAS_BREAKOUT = True
except ImportError:
    _HAS_BREAKOUT = False

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
# Priority coin lists (kept short to avoid Render free-tier timeout)
# ---------------------------------------------------------------------------

# 30 highest-liquidity / highest-volatility coins for the Breakout scan.
# Scanning 4 timeframes × 30 coins = 120 kline fetches; fits within 90s.
BREAKOUT_PRIORITY = [
    # Tier 1 majors
    "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD",
    # Large caps with strong breakout tendencies
    "AVAXUSD", "SUIUSD", "DOTD", "LINKUSD", "MATICUSD",
    # High-beta / high-volatility
    "PEPEUSD", "DOGEUSD", "SHIBUSD", "WIFUSD", "BONKUSD",
    "FLOKIUSD", "MOGUSD", "PONKEUSD", "MEMEUSD", "DOGUSD",
    # Mid-cap momentum
    "INJUSD", "TIAUSD", "OPUSD", "ARBUSD", "APTUSD",
    # DeFi blue-chips
    "UNIUSD", "AAVEUSD", "JUPUSD",
    # Narrative / trending
    "WLDUSD", "PYTHUSD",
]

# 40 coins for the SMC scan (15m only — lighter than breakout).
SMC_PRIORITY = [
    "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD",
    "AVAXUSD", "SUIUSD", "DOTD", "LINKUSD", "MATICUSD",
    "PEPEUSD", "DOGEUSD", "SHIBUSD", "WIFUSD", "BONKUSD",
    "FLOKIUSD", "MOGUSD", "PONKEUSD", "MEMEUSD", "DOGUSD",
    "INJUSD", "TIAUSD", "OPUSD", "ARBUSD", "APTUSD",
    "UNIUSD", "AAVEUSD", "JUPUSD", "WLDUSD", "PYTHUSD",
    "SEIUSD", "ORDIUSD", "STXUSD", "RUNEUSD", "LDOUSD",
    "ENAUSD", "ATHEUSD", "TRUMPUSD", "POLUSD", "IOTUSD",
]


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "time": time.time(),
        "engines": {
            "smc": _HAS_SMC,
            "breakout": _HAS_BREAKOUT,
        }
    })


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


# ---------------------------------------------------------------------------
# SMC scan endpoint
# ---------------------------------------------------------------------------
@app.route("/api/scan/smc")
def scan_smc():
    """
    Smart Money Concepts scan.

    Query params:
      top_n     (int, default 20) — return this many results sorted by confidence
      min_score (int, default 50) — minimum confidence score to include
    """
    if not _HAS_SMC:
        return jsonify({"error": "smc_engine.py not found on server — upload it to backend/"}), 503

    top_n = int(request.args.get("top_n", 20))
    min_score = int(request.args.get("min_score", 50))

    symbols = SMC_PRIORITY
    logger.info(f"SMC scan: {len(symbols)} coins, top_n={top_n}, min_score={min_score}")

    # Fetch 15m candles for all SMC-priority coins in a single batch pass.
    raw = fetch_universe_klines(symbols, interval="15m", limit=100)

    results = []
    for symbol in symbols:
        payload = raw.get(symbol, {})
        candles = payload.get("candles")
        if not candles or len(candles) < 50:
            logger.warning(f"SMC skip {symbol}: only {len(candles) if candles else 0} candles")
            continue
        try:
            sig = run_smc_scan(symbol, candles)
            if sig and sig.get("confidence", 0) >= min_score:
                results.append(sig)
        except Exception as e:
            logger.error(f"SMC error {symbol}: {e}")

    # Sort by confidence descending, return top_n
    results.sort(key=lambda x: x.get("confidence", 0), reverse=True)
    results = results[:top_n]

    return jsonify({
        "scan": "smc",
        "count": len(results),
        "scanned": len(symbols),
        "results": results,
    })


# ---------------------------------------------------------------------------
# Breakout scan endpoint
# ---------------------------------------------------------------------------
@app.route("/api/scan/breakout")
def scan_breakout():
    """
    Multi-timeframe breakout + retest scan.

    Query params:
      top_n     (int, default 25) — return this many results sorted by score
      min_score (int, default 40) — minimum score to include
    """
    if not _HAS_BREAKOUT:
        return jsonify({"error": "breakout_engine.py not found on server — upload it to backend/"}), 503

    top_n = int(request.args.get("top_n", 25))
    min_score = int(request.args.get("min_score", 40))

    symbols = BREAKOUT_PRIORITY
    logger.info(f"Breakout scan: {len(symbols)} coins, top_n={top_n}, min_score={min_score}")

    # Fetch all four timeframes in parallel batch passes.
    # 4H: 100 candles (~16 days), 1H: 100 candles (~4 days),
    # 15m: 100 candles (~25 hrs), 5m: 100 candles (~8 hrs).
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=4) as pool:
        f4h  = pool.submit(fetch_universe_klines, symbols, "4h",  100)
        f1h  = pool.submit(fetch_universe_klines, symbols, "1h",  100)
        f15m = pool.submit(fetch_universe_klines, symbols, "15m", 100)
        f5m  = pool.submit(fetch_universe_klines, symbols, "5m",  100)
        raw_4h  = f4h.result()
        raw_1h  = f1h.result()
        raw_15m = f15m.result()
        raw_5m  = f5m.result()

    fetch_ms = int((time.time() - t0) * 1000)
    logger.info(f"Breakout fetch complete in {fetch_ms}ms")

    results = []
    for symbol in symbols:
        c4h  = (raw_4h.get(symbol)  or {}).get("candles")
        c1h  = (raw_1h.get(symbol)  or {}).get("candles")
        c15m = (raw_15m.get(symbol) or {}).get("candles")
        c5m  = (raw_5m.get(symbol)  or {}).get("candles")

        # Need at least 4H and 1H data to be useful
        if not c4h or len(c4h) < 30 or not c1h or len(c1h) < 30:
            logger.warning(f"Breakout skip {symbol}: insufficient 4H/1H data")
            continue

        try:
            sig = run_breakout_scan(symbol, c4h, c1h, c15m or [], c5m or [])
            if sig and sig.get("score", 0) >= min_score:
                results.append(sig)
        except Exception as e:
            logger.error(f"Breakout error {symbol}: {e}")

    # Sort by score descending, return top_n
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    results = results[:top_n]

    return jsonify({
        "scan": "breakout",
        "count": len(results),
        "scanned": len(symbols),
        "fetch_ms": fetch_ms,
        "results": results,
    })


# ---------------------------------------------------------------------------
# Heatmap
# ---------------------------------------------------------------------------
@app.route("/api/heatmap")
def heatmap():
    symbols = all_symbols()
    raw = fetch_universe_klines(symbols, interval="1h", limit=30)
    symbol_candles = {s: payload.get("candles") for s, payload in raw.items() if payload.get("candles")}

    # Overlay a quick intraday-style signal per coin using the same 1h
    # candles already fetched for the heatmap (avoids a second network
    # round-trip just to color/badge each cell with direction+confidence).
    scan_results = {}
    for symbol, candles in symbol_candles.items():
        if candles and len(candles) >= 25:
            scan_results[symbol] = quick_signal(candles)

    data = build_heatmap(symbol_candles, scan_results_by_symbol=scan_results)
    return jsonify(data)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
