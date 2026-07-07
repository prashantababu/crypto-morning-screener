"""
Multi-source crypto price waterfall.

Mirrors the broker-fallback pattern from the India Trader Alert Engine
(Angel One -> Fyers -> Dhan -> Zerodha -> yfinance), adapted for crypto:

    CoinDCX -> Delta Exchange -> Binance (public, no key) -> CoinGecko (last resort)

Each source implements the same interface so the waterfall can fall through
cleanly on timeout, rate-limit, or symbol-not-found. All sources here use
PUBLIC endpoints only (no API keys), since this screener is read-only market
data, not account/order data.

Candle shape returned by every source (normalized):
    {"open_time": ms, "open": float, "high": float, "low": float,
     "close": float, "volume": float}
"""

import time
import logging
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger("price_waterfall")

REQUEST_TIMEOUT = 6  # seconds, per source attempt
INTERVAL_MAP_BINANCE = {
    "1m": "1m", "5m": "5m", "15m": "15m", "1h": "1h", "4h": "4h", "1d": "1d",
}


class SourceError(Exception):
    pass


# ---------------------------------------------------------------------------
# Source 1: CoinDCX (public market data API)
# ---------------------------------------------------------------------------
class CoinDCXSource:
    name = "coindcx"
    BASE = "https://public.coindcx.com"

    def to_dcx_symbol(self, symbol):
        # CoinDCX uses e.g. "B-BTC_USDT" style market names for futures,
        # but ticker endpoint uses raw pair like "BTCUSDT". Kept simple here;
        # production build should map against /exchange/v1/markets_details.
        return symbol

    def get_klines(self, symbol, interval="1h", limit=100):
        # CoinDCX's public candle API (data.coindcx.com) historically used
        # pair names like "B-BTC_USDT". This is a best-effort source; if it
        # 404s/422s the waterfall falls through automatically.
        pair = f"B-{symbol.replace('USDT', '')}_USDT"
        url = "https://public.coindcx.com/market_data/candles"
        params = {"pair": pair, "interval": interval, "limit": limit}
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            raise SourceError(f"coindcx http {r.status_code}")
        data = r.json()
        if not isinstance(data, list) or not data:
            raise SourceError("coindcx empty response")
        candles = []
        for row in data:
            candles.append({
                "open_time": row.get("time"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })
        candles.sort(key=lambda c: c["open_time"])
        return candles


# ---------------------------------------------------------------------------
# Source 2: Delta Exchange (public market data API)
# ---------------------------------------------------------------------------
class DeltaExchangeSource:
    name = "delta_exchange"
    BASE = "https://api.india.delta.exchange"

    def to_delta_symbol(self, symbol):
        # Delta India perpetuals are typically named like "BTCUSD" / "ETHUSD"
        # for majors. Many alt perps are not listed on Delta at all, which is
        # expected -> waterfall falls through to Binance for those.
        return symbol.replace("USDT", "USD")

    def get_klines(self, symbol, interval="1h", limit=100):
        delta_symbol = self.to_delta_symbol(symbol)
        resolution_map = {"1m": "1", "5m": "5", "15m": "15", "1h": "60", "4h": "240", "1d": "1D"}
        resolution = resolution_map.get(interval, "60")
        end = int(time.time())
        start = end - limit * _interval_seconds(interval)
        url = f"{self.BASE}/v2/history/candles"
        params = {"resolution": resolution, "symbol": delta_symbol, "start": start, "end": end}
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            raise SourceError(f"delta http {r.status_code}")
        payload = r.json()
        rows = payload.get("result", [])
        if not rows:
            raise SourceError("delta empty response")
        candles = []
        for row in rows:
            candles.append({
                "open_time": int(row["time"]) * 1000,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": float(row.get("volume", 0)),
            })
        candles.sort(key=lambda c: c["open_time"])
        return candles


# ---------------------------------------------------------------------------
# Source 3: Binance public REST (no key needed, deepest liquidity proxy)
# ---------------------------------------------------------------------------
class BinanceSource:
    name = "binance"
    BASE = "https://api.binance.com"

    def get_klines(self, symbol, interval="1h", limit=100):
        binance_interval = INTERVAL_MAP_BINANCE.get(interval, "1h")
        url = f"{self.BASE}/api/v3/klines"
        params = {"symbol": symbol, "interval": binance_interval, "limit": limit}
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            raise SourceError(f"binance http {r.status_code}")
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            raise SourceError("binance empty response")
        candles = []
        for row in rows:
            candles.append({
                "open_time": row[0],
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            })
        return candles


# ---------------------------------------------------------------------------
# Source 4: CoinGecko (last resort, daily-granularity friendly)
# ---------------------------------------------------------------------------
class CoinGeckoSource:
    name = "coingecko"
    BASE = "https://api.coingecko.com/api/v3"
    # Minimal symbol -> coingecko id map for the watchlist; extend as needed.
    SYMBOL_TO_ID = {
        "BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana",
        "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano",
        "AVAXUSDT": "avalanche-2", "DOGEUSDT": "dogecoin", "LTCUSDT": "litecoin",
        "LINKUSDT": "chainlink", "DOTUSDT": "polkadot", "MATICUSDT": "matic-network",
    }

    def get_klines(self, symbol, interval="1h", limit=100):
        coin_id = self.SYMBOL_TO_ID.get(symbol)
        if not coin_id:
            raise SourceError(f"coingecko has no id mapping for {symbol}")
        days = 1 if interval in ("1m", "5m", "15m", "1h") else 14
        url = f"{self.BASE}/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": days}
        r = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if r.status_code != 200:
            raise SourceError(f"coingecko http {r.status_code}")
        rows = r.json()
        if not isinstance(rows, list) or not rows:
            raise SourceError("coingecko empty response")
        candles = []
        for row in rows[-limit:]:
            candles.append({
                "open_time": row[0],
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": 0.0,  # OHLC endpoint doesn't include volume
            })
        return candles


def _interval_seconds(interval):
    return {"1m": 60, "5m": 300, "15m": 900, "1h": 3600, "4h": 14400, "1d": 86400}.get(interval, 3600)


# ---------------------------------------------------------------------------
# Waterfall orchestration
# ---------------------------------------------------------------------------
WATERFALL = [CoinDCXSource(), DeltaExchangeSource(), BinanceSource(), CoinGeckoSource()]


def get_klines_with_fallback(symbol, interval="1h", limit=100):
    """
    Try each source in priority order. Returns (candles, source_name).
    Raises SourceError only if every source in the chain fails.
    """
    errors = []
    for source in WATERFALL:
        try:
            candles = source.get_klines(symbol, interval=interval, limit=limit)
            if candles and len(candles) >= 20:  # need enough bars for EMA21/RSI14
                return candles, source.name
            errors.append(f"{source.name}: insufficient bars ({len(candles) if candles else 0})")
        except Exception as e:
            errors.append(f"{source.name}: {e}")
            continue
    raise SourceError(f"All sources failed for {symbol}: {'; '.join(errors)}")


def fetch_universe_klines(symbols, interval="1h", limit=100, max_workers=8):
    """
    Fetch klines for many symbols in parallel, each with its own waterfall.
    Returns dict: {symbol: {"candles": [...], "source": "binance"} or {"error": "..."}}
    """
    results = {}

    def _fetch_one(sym):
        try:
            candles, source = get_klines_with_fallback(sym, interval=interval, limit=limit)
            return sym, {"candles": candles, "source": source}
        except SourceError as e:
            return sym, {"error": str(e)}

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(_fetch_one, s) for s in symbols]
        for fut in as_completed(futures):
            sym, payload = fut.result()
            results[sym] = payload

    return results
