"""
Test-only entrypoint: runs the real Flask app but monkey-patches the price
waterfall to return synthetic OHLCV data instead of hitting live exchange
APIs (which are not reachable from this sandbox). This lets us verify the
full HTTP server -> route -> engine -> JSON response pipeline end-to-end,
exactly as the dashboard frontend will call it.

NOT for production use -- this is purely so Claude can verify the dashboard
against a live server during this build. Delete or ignore this file when
running for real; app.py talks to real exchanges via price_waterfall.py.
"""
import sys
import os
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "sources"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "strategies"))

import price_waterfall


def fake_get_klines_with_fallback(symbol, interval="1h", limit=100):
    random.seed(hash(symbol + interval) % (2**31))
    candles = []
    price = 100 + (hash(symbol) % 1000) / 10
    drift = random.uniform(-0.3, 0.3)
    for i in range(limit):
        o = price
        move = drift + random.uniform(-1.5, 1.5)
        c = max(o + move, 0.01)
        h = max(o, c) + random.uniform(0, 0.5)
        l = max(min(o, c) - random.uniform(0, 0.5), 0.01)
        vol = random.uniform(800, 1500)
        candles.append({"open_time": i * 3600000, "open": o, "high": h, "low": l, "close": c, "volume": vol})
        price = c
    return candles, "synthetic_test_source"


def fake_fetch_universe_klines(symbols, interval="1h", limit=100, max_workers=8):
    out = {}
    for s in symbols:
        candles, source = fake_get_klines_with_fallback(s, interval, limit)
        out[s] = {"candles": candles, "source": source}
    return out


price_waterfall.get_klines_with_fallback = fake_get_klines_with_fallback
price_waterfall.fetch_universe_klines = fake_fetch_universe_klines

import app as app_module
app_module.get_klines_with_fallback = fake_get_klines_with_fallback
app_module.fetch_universe_klines = fake_fetch_universe_klines

if __name__ == "__main__":
    app_module.app.run(host="0.0.0.0", port=5050, debug=False)
