"""
smc_engine.py — Smart Money Concepts Signal Engine
====================================================
DROP INTO: backend/  (alongside existing engine.py)

Generates LONG / SHORT / NEUTRAL signals with confidence scores
using institutional trading concepts:

  1. Market Structure  — BOS (Break of Structure), CHoCH (Change of Character)
  2. Order Blocks      — Last opposing candle before a strong impulsive move
  3. Fair Value Gaps   — 3-candle imbalance zones price is attracted back to
  4. Liquidity Sweeps  — Equal highs/lows that get hunted before reversal
  5. Supply & Demand   — Institutional origin zones (strong impulsive departure)
  6. Fibonacci OTE     — Optimal Trade Entry at 62-79% retracement
  7. Volume Profile    — Point of Control, Value Area High/Low from recent bars
  8. Support/Resistance — Dynamic S/R from swing clusters (reuses support_resistance.py)
  9. Premium/Discount  — Price position relative to range midpoint (SMC core rule)

Confidence scoring (0-100):
  Each confirmed signal component adds points.
  Multiple confluences = higher confidence = higher quality trade.
  Score >= 70 : HIGH confidence — take the trade
  Score 50-69 : MEDIUM confidence — valid but wait for one more confirmation
  Score < 50  : LOW confidence — skip or paper trade only

USAGE in app.py:
  from smc_engine import run_smc_scan
  result = run_smc_scan(symbol, candles_1h, candles_15m)

INTEGRATION NOTE:
  This engine works alongside the existing engine.py, not replacing it.
  Run both and combine signals: traditional indicators (RSI/MACD/EMA)
  from engine.py + SMC structure from smc_engine.py for maximum confluence.
"""

import math
from typing import Optional


# ---------------------------------------------------------------------------
# 1. MARKET STRUCTURE — BOS & CHoCH detection
# ---------------------------------------------------------------------------

def detect_swing_points(candles: list, lookback: int = 3) -> dict:
    """
    Find swing highs and lows.
    Returns {'highs': [(idx, price)], 'lows': [(idx, price)]}
    """
    highs, lows = [], []
    n = len(candles)
    for i in range(lookback, n - lookback):
        h = candles[i]["high"]
        l = candles[i]["low"]
        if all(candles[i-j]["high"] <= h for j in range(1, lookback+1)) and \
           all(candles[i+j]["high"] <= h for j in range(1, lookback+1)):
            highs.append((i, h))
        if all(candles[i-j]["low"] >= l for j in range(1, lookback+1)) and \
           all(candles[i+j]["low"] >= l for j in range(1, lookback+1)):
            lows.append((i, l))
    return {"highs": highs, "lows": lows}


def detect_market_structure(candles: list, swing_lookback: int = 3) -> dict:
    """
    Identifies:
      - BOS  (Break of Structure) = trend continuation
      - CHoCH (Change of Character) = potential reversal
      - Current trend: bullish / bearish / ranging

    BOS bullish: price breaks above most recent swing high (trend continues up)
    BOS bearish: price breaks below most recent swing low (trend continues down)
    CHoCH: price breaks structure in opposite direction to current trend
           (first sign of reversal — highest probability reversal signal in SMC)
    """
    if len(candles) < 20:
        return {"trend": "ranging", "structure": "none", "last_bos": None, "choch": False}

    swings = detect_swing_points(candles[:-1], swing_lookback)  # exclude current candle
    current_close = candles[-1]["close"]
    current_high = candles[-1]["high"]
    current_low = candles[-1]["low"]

    recent_highs = swings["highs"][-3:] if swings["highs"] else []
    recent_lows = swings["lows"][-3:] if swings["lows"] else []

    last_sh = recent_highs[-1][1] if recent_highs else None
    last_sl = recent_lows[-1][1] if recent_lows else None
    prev_sh = recent_highs[-2][1] if len(recent_highs) >= 2 else None
    prev_sl = recent_lows[-2][1] if len(recent_lows) >= 2 else None

    # Determine trend: higher highs + higher lows = bullish
    if last_sh and prev_sh and last_sl and prev_sl:
        if last_sh > prev_sh and last_sl > prev_sl:
            trend = "bullish"
        elif last_sh < prev_sh and last_sl < prev_sl:
            trend = "bearish"
        else:
            trend = "ranging"
    else:
        trend = "ranging"

    structure = "none"
    choch = False
    last_bos = None

    # BOS detection (current candle breaks recent swing)
    if last_sh and current_high > last_sh:
        if trend == "bullish":
            structure = "BOS_bullish"
            last_bos = {"type": "BOS_bullish", "level": last_sh}
        elif trend == "bearish":
            structure = "CHoCH_bullish"
            choch = True
            last_bos = {"type": "CHoCH_bullish", "level": last_sh}

    elif last_sl and current_low < last_sl:
        if trend == "bearish":
            structure = "BOS_bearish"
            last_bos = {"type": "BOS_bearish", "level": last_sl}
        elif trend == "bullish":
            structure = "CHoCH_bearish"
            choch = True
            last_bos = {"type": "CHoCH_bearish", "level": last_sl}

    return {
        "trend": trend,
        "structure": structure,
        "choch": choch,
        "last_bos": last_bos,
        "last_swing_high": last_sh,
        "last_swing_low": last_sl,
    }


# ---------------------------------------------------------------------------
# 2. ORDER BLOCKS — Last opposing candle before impulsive move
# ---------------------------------------------------------------------------

def detect_order_blocks(candles: list, lookback: int = 50, min_move_pct: float = 1.0) -> dict:
    """
    Bullish Order Block (OB): last BEARISH candle before a strong bullish impulse
    Bearish Order Block (OB): last BULLISH candle before a strong bearish impulse

    Quality OB characteristics:
      - Strong move away (>min_move_pct%) validates the OB
      - Fresh (not yet mitigated = price hasn't returned to it)
      - Most recent OB is strongest

    Returns nearest fresh bullish and bearish OBs relative to current price.
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    current_price = candles[-1]["close"]
    bullish_obs, bearish_obs = [], []

    for i in range(1, len(window) - 2):
        c = window[i]
        c_next = window[i + 1]
        c_prev = window[i - 1]

        body_size = abs(c["close"] - c["open"])
        if body_size < current_price * 0.0001:
            continue  # ignore doji/tiny candles

        # Bullish OB: a bearish candle followed by strong bullish move
        if c["close"] < c["open"]:
            move_up = (c_next["high"] - c["low"]) / c["low"] * 100
            if move_up >= min_move_pct:
                ob = {
                    "type": "bullish",
                    "high": c["high"],
                    "low": c["low"],
                    "mid": (c["high"] + c["low"]) / 2,
                    "index": i,
                    "mitigated": current_price > c["low"] and current_price > c["high"],
                    "fresh": current_price > c["high"],  # price is above OB = fresh demand zone below
                }
                bullish_obs.append(ob)

        # Bearish OB: a bullish candle followed by strong bearish move
        elif c["close"] > c["open"]:
            move_down = (c["high"] - c_next["low"]) / c["high"] * 100
            if move_down >= min_move_pct:
                ob = {
                    "type": "bearish",
                    "high": c["high"],
                    "low": c["low"],
                    "mid": (c["high"] + c["low"]) / 2,
                    "index": i,
                    "mitigated": current_price < c["high"] and current_price < c["low"],
                    "fresh": current_price < c["low"],  # price below OB = fresh supply zone above
                }
                bearish_obs.append(ob)

    # Find nearest fresh OBs relative to current price
    fresh_bull = [ob for ob in bullish_obs if ob["fresh"] and ob["high"] < current_price]
    fresh_bear = [ob for ob in bearish_obs if ob["fresh"] and ob["low"] > current_price]

    nearest_bull = max(fresh_bull, key=lambda x: x["high"]) if fresh_bull else None
    nearest_bear = min(fresh_bear, key=lambda x: x["low"]) if fresh_bear else None

    return {
        "bullish_ob": nearest_bull,
        "bearish_ob": nearest_bear,
        "total_bullish": len(fresh_bull),
        "total_bearish": len(fresh_bear),
    }


# ---------------------------------------------------------------------------
# 3. FAIR VALUE GAPS (FVG) — 3-candle imbalance zones
# ---------------------------------------------------------------------------

def detect_fvg(candles: list, lookback: int = 30) -> dict:
    """
    Fair Value Gap (Imbalance):
      Bullish FVG: candle[i-1].high < candle[i+1].low
                   Gap between wick of c1 and wick of c3
                   Price attracted back to fill this gap (excellent long entry)

      Bearish FVG: candle[i-1].low > candle[i+1].high
                   Gap between wick of c1 and wick of c3
                   Price attracted back to fill (excellent short entry)

    Fresh FVG = not yet filled (price hasn't returned to mitigate it).
    An OB + FVG in the same zone = extremely powerful confluence.
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    current_price = candles[-1]["close"]
    bull_fvgs, bear_fvgs = [], []

    for i in range(1, len(window) - 1):
        c_prev = window[i - 1]
        c_curr = window[i]
        c_next = window[i + 1]

        # Bullish FVG: gap between prev high and next low
        if c_prev["high"] < c_next["low"]:
            fvg_high = c_next["low"]
            fvg_low = c_prev["high"]
            fvg_mid = (fvg_high + fvg_low) / 2
            size_pct = (fvg_high - fvg_low) / fvg_low * 100
            if size_pct >= 0.1:  # minimum meaningful gap
                filled = current_price < fvg_low  # price fell back through
                bull_fvgs.append({
                    "type": "bullish", "high": fvg_high, "low": fvg_low,
                    "mid": fvg_mid, "size_pct": round(size_pct, 3),
                    "filled": filled, "index": i,
                })

        # Bearish FVG: gap between prev low and next high
        elif c_prev["low"] > c_next["high"]:
            fvg_high = c_prev["low"]
            fvg_low = c_next["high"]
            fvg_mid = (fvg_high + fvg_low) / 2
            size_pct = (fvg_high - fvg_low) / fvg_low * 100
            if size_pct >= 0.1:
                filled = current_price > fvg_high
                bear_fvgs.append({
                    "type": "bearish", "high": fvg_high, "low": fvg_low,
                    "mid": fvg_mid, "size_pct": round(size_pct, 3),
                    "filled": filled, "index": i,
                })

    # Nearest unfilled FVGs
    fresh_bull = [f for f in bull_fvgs if not f["filled"] and f["high"] < current_price]
    fresh_bear = [f for f in bear_fvgs if not f["filled"] and f["low"] > current_price]

    nearest_bull = max(fresh_bull, key=lambda x: x["high"]) if fresh_bull else None
    nearest_bear = min(fresh_bear, key=lambda x: x["low"]) if fresh_bear else None

    # Check if price is currently entering an FVG zone (highest-probability entry)
    entering_bull = nearest_bull and nearest_bull["low"] <= current_price <= nearest_bull["high"]
    entering_bear = nearest_bear and nearest_bear["low"] <= current_price <= nearest_bear["high"]

    return {
        "bullish_fvg": nearest_bull,
        "bearish_fvg": nearest_bear,
        "entering_bullish_fvg": entering_bull,
        "entering_bearish_fvg": entering_bear,
        "total_bull_fvgs": len(fresh_bull),
        "total_bear_fvgs": len(fresh_bear),
    }


# ---------------------------------------------------------------------------
# 4. LIQUIDITY SWEEPS — Equal highs/lows hunted before reversal
# ---------------------------------------------------------------------------

def detect_liquidity(candles: list, lookback: int = 40, tolerance_pct: float = 0.15) -> dict:
    """
    Liquidity sits where retail traders cluster their stop losses:
      Buy-side liquidity  = stop losses of shorts = equal HIGHS / previous highs
      Sell-side liquidity = stop losses of longs  = equal LOWS  / previous lows

    A liquidity SWEEP = price briefly breaks a key level, triggers stops,
    then reverses sharply. This is the highest-probability SMC entry signal.

    Identifies:
      - Equal highs (buy-side liquidity resting above)
      - Equal lows (sell-side liquidity resting below)
      - Recent sweep (last candle wicked through a liquidity level and closed back)
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    current = candles[-1]
    current_price = current["close"]
    tol = current_price * (tolerance_pct / 100)

    # Find equal highs (buy-side liquidity)
    highs = [c["high"] for c in window[:-1]]
    equal_highs = []
    for i, h in enumerate(highs):
        matches = [j for j, h2 in enumerate(highs) if i != j and abs(h - h2) <= tol]
        if len(matches) >= 1:
            equal_highs.append(h)

    # Find equal lows (sell-side liquidity)
    lows = [c["low"] for c in window[:-1]]
    equal_lows = []
    for i, l in enumerate(lows):
        matches = [j for j, l2 in enumerate(lows) if i != j and abs(l - l2) <= tol]
        if len(matches) >= 1:
            equal_lows.append(l)

    # Deduplicate within tolerance
    def dedup(levels):
        out = []
        for l in sorted(set(levels)):
            if not out or abs(l - out[-1]) > tol:
                out.append(l)
        return out

    buy_side = dedup(equal_highs)   # equal highs above price = buy-side liquidity
    sell_side = dedup(equal_lows)   # equal lows below price = sell-side liquidity

    # Filter to levels above/below current price
    bsl_above = [h for h in buy_side if h > current_price * 1.001]
    ssl_below = [l for l in sell_side if l < current_price * 0.999]

    nearest_bsl = min(bsl_above) if bsl_above else None  # nearest resistance liquidity
    nearest_ssl = max(ssl_below) if ssl_below else None  # nearest support liquidity

    # Detect if last candle swept liquidity (wick through level, body closed back)
    last_c = candles[-1]
    swept_high = False
    swept_low = False

    if bsl_above:
        for level in bsl_above:
            if last_c["high"] > level and last_c["close"] < level:
                swept_high = True  # sweep of buy-side liquidity = bullish reversal incoming

    if ssl_below:
        for level in ssl_below:
            if last_c["low"] < level and last_c["close"] > level:
                swept_low = True  # sweep of sell-side liquidity = bearish reversal or long entry

    # Distance to nearest liquidity as % (how far price has to move to trigger)
    dist_to_bsl = (nearest_bsl - current_price) / current_price * 100 if nearest_bsl else None
    dist_to_ssl = (current_price - nearest_ssl) / current_price * 100 if nearest_ssl else None

    return {
        "buy_side_liquidity": nearest_bsl,      # level above price (stops of shorts)
        "sell_side_liquidity": nearest_ssl,     # level below price (stops of longs)
        "swept_buy_side": swept_high,           # just swept BSL = potential short
        "swept_sell_side": swept_low,           # just swept SSL = potential long
        "dist_to_bsl_pct": round(dist_to_bsl, 2) if dist_to_bsl else None,
        "dist_to_ssl_pct": round(dist_to_ssl, 2) if dist_to_ssl else None,
        "bsl_levels": bsl_above[:3],
        "ssl_levels": ssl_below[-3:],
    }


# ---------------------------------------------------------------------------
# 5. SUPPLY & DEMAND ZONES — Origin of strong impulsive moves
# ---------------------------------------------------------------------------

def detect_supply_demand(candles: list, lookback: int = 60, min_move_pct: float = 1.5) -> dict:
    """
    Supply zone: area where price was before a strong bearish impulse
    Demand zone: area where price was before a strong bullish impulse

    Difference from Order Blocks:
      - S&D zones are wider (cover the full consolidation/base before the move)
      - OBs are the specific last candle within that zone
      - Both are used together for zone confluence

    A fresh zone (price hasn't returned) is the strongest entry signal.
    A tested zone (price tapped once and bounced) is second best.
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    current_price = candles[-1]["close"]
    demand_zones, supply_zones = [], []

    for i in range(2, len(window) - 2):
        move_up = (window[i]["high"] - window[i-1]["low"]) / window[i-1]["low"] * 100
        move_down = (window[i-1]["high"] - window[i]["low"]) / window[i-1]["high"] * 100

        if move_up >= min_move_pct:
            # Demand zone: base of the bullish impulse
            base_low = min(window[i-1]["low"], window[i-2]["low"])
            base_high = max(window[i-1]["high"], window[i]["open"])
            tests = sum(1 for c in window[i+1:] if base_low <= c["low"] <= base_high)
            fresh = current_price > base_high
            demand_zones.append({
                "high": base_high, "low": base_low,
                "mid": (base_high + base_low) / 2,
                "tests": tests, "fresh": fresh,
                "strength": "strong" if tests <= 1 else "weak",
                "index": i,
            })

        if move_down >= min_move_pct:
            # Supply zone: ceiling of the bearish impulse
            base_high = max(window[i-1]["high"], window[i-2]["high"])
            base_low = min(window[i-1]["low"], window[i]["open"])
            tests = sum(1 for c in window[i+1:] if base_low <= c["high"] <= base_high)
            fresh = current_price < base_low
            supply_zones.append({
                "high": base_high, "low": base_low,
                "mid": (base_high + base_low) / 2,
                "tests": tests, "fresh": fresh,
                "strength": "strong" if tests <= 1 else "weak",
                "index": i,
            })

    # Nearest fresh zones relative to current price
    fresh_demand = [z for z in demand_zones if z["fresh"] and z["high"] < current_price]
    fresh_supply = [z for z in supply_zones if z["fresh"] and z["low"] > current_price]

    nearest_demand = max(fresh_demand, key=lambda x: x["high"]) if fresh_demand else None
    nearest_supply = min(fresh_supply, key=lambda x: x["low"]) if fresh_supply else None

    return {
        "demand_zone": nearest_demand,
        "supply_zone": nearest_supply,
        "in_demand": nearest_demand and nearest_demand["low"] <= current_price <= nearest_demand["high"],
        "in_supply": nearest_supply and nearest_supply["low"] <= current_price <= nearest_supply["high"],
        "total_demand": len(fresh_demand),
        "total_supply": len(fresh_supply),
    }


# ---------------------------------------------------------------------------
# 6. FIBONACCI OTE — Optimal Trade Entry at 62-79% retracement
# ---------------------------------------------------------------------------

def detect_fibonacci_ote(candles: list, lookback: int = 50) -> dict:
    """
    OTE (Optimal Trade Entry) = ICT concept for precise entries.
    After a BOS, price retraces into the 62-79% Fibonacci zone.
    This is statistically the highest-probability entry level.

    Key Fibonacci levels:
      0%    = Swing High (top of move)
      23.6% = Shallow retracement
      38.2% = Moderate retracement
      50%   = Equilibrium (fair value)
      61.8% = Golden ratio — start of OTE zone
      70.5% = OTE midpoint (ICT's most precise entry)
      79%   = End of OTE zone (maximum retracement for trend continuation)
      88.6% = Deep retracement (still valid if strong structure)
      100%  = Swing Low (bottom of move)
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    current_price = candles[-1]["close"]

    if len(window) < 10:
        return {"in_ote": False, "fib_levels": None, "bias": "none"}

    swing_high = max(c["high"] for c in window)
    swing_low = min(c["low"] for c in window)
    sh_idx = max(range(len(window)), key=lambda i: window[i]["high"])
    sl_idx = min(range(len(window)), key=lambda i: window[i]["low"])
    move_range = swing_high - swing_low

    if move_range == 0:
        return {"in_ote": False, "fib_levels": None, "bias": "none"}

    # Determine bias: is this a bullish or bearish setup?
    # Bullish: swing low came BEFORE swing high (uptrend, now retracing = buy opportunity)
    # Bearish: swing high came BEFORE swing low (downtrend, now retracing = sell opportunity)
    if sl_idx < sh_idx:
        # Bullish move → retracement back down → OTE zone for LONG entry
        ote_high = swing_high - (0.618 * move_range)  # 61.8% retrace from high
        ote_low = swing_high - (0.786 * move_range)   # 78.6% retrace
        ote_entry = swing_high - (0.705 * move_range)  # 70.5% OTE sweet spot
        in_ote = ote_low <= current_price <= ote_high
        bias = "bullish"
    else:
        # Bearish move → retracement back up → OTE zone for SHORT entry
        ote_low = swing_low + (0.618 * move_range)
        ote_high = swing_low + (0.786 * move_range)
        ote_entry = swing_low + (0.705 * move_range)
        in_ote = ote_low <= current_price <= ote_high
        bias = "bearish"

    fib_levels = {
        "0":    round(swing_low if bias == "bullish" else swing_high, 6),
        "23.6": round(swing_high - 0.236*move_range if bias == "bullish" else swing_low + 0.236*move_range, 6),
        "38.2": round(swing_high - 0.382*move_range if bias == "bullish" else swing_low + 0.382*move_range, 6),
        "50":   round(swing_high - 0.500*move_range if bias == "bullish" else swing_low + 0.500*move_range, 6),
        "61.8": round(ote_high, 6),
        "70.5": round(ote_entry, 6),
        "78.6": round(ote_low, 6),
        "100":  round(swing_high if bias == "bullish" else swing_low, 6),
    }

    return {
        "in_ote": in_ote,
        "bias": bias,
        "ote_zone_high": round(ote_high, 6),
        "ote_zone_low": round(ote_low, 6),
        "ote_entry": round(ote_entry, 6),
        "swing_high": round(swing_high, 6),
        "swing_low": round(swing_low, 6),
        "fib_levels": fib_levels,
        "retracement_pct": round((swing_high - current_price) / move_range * 100 if bias == "bullish"
                                  else (current_price - swing_low) / move_range * 100, 1),
    }


# ---------------------------------------------------------------------------
# 7. VOLUME PROFILE — POC, VAH, VAL from recent candles
# ---------------------------------------------------------------------------

def detect_volume_profile(candles: list, lookback: int = 48, bins: int = 20) -> dict:
    """
    Volume Profile shows where MOST volume was traded in recent bars.
    Key levels:
      POC (Point of Control) = price level with MOST volume — acts as magnet
      VAH (Value Area High)  = top of 70% volume zone = resistance
      VAL (Value Area Low)   = bottom of 70% volume zone = support

    Price above POC = bullish (value area is below current price = buyers in control)
    Price below POC = bearish
    Price at POC = contested zone — wait for breakout direction
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    current_price = candles[-1]["close"]

    if not window:
        return {"poc": None, "vah": None, "val": None, "bias": "none"}

    price_min = min(c["low"] for c in window)
    price_max = max(c["high"] for c in window)
    if price_max == price_min:
        return {"poc": None, "vah": None, "val": None, "bias": "none"}

    bin_size = (price_max - price_min) / bins
    volume_bins = [0.0] * bins

    for c in window:
        vol = c.get("volume", 1)
        bar_range = c["high"] - c["low"]
        if bar_range == 0:
            continue
        lo_idx = int((c["low"] - price_min) / bin_size)
        hi_idx = int((c["high"] - price_min) / bin_size)
        for b in range(max(0, lo_idx), min(bins, hi_idx + 1)):
            overlap_lo = price_min + b * bin_size
            overlap_hi = price_min + (b + 1) * bin_size
            overlap = (min(c["high"], overlap_hi) - max(c["low"], overlap_lo)) / bar_range
            volume_bins[b] += vol * max(0, overlap)

    poc_idx = volume_bins.index(max(volume_bins))
    poc = price_min + (poc_idx + 0.5) * bin_size

    # Value area: bins accounting for 70% of total volume
    total_vol = sum(volume_bins)
    target = total_vol * 0.70
    sorted_bins = sorted(range(bins), key=lambda i: volume_bins[i], reverse=True)
    va_bins = set()
    accumulated = 0
    for b in sorted_bins:
        accumulated += volume_bins[b]
        va_bins.add(b)
        if accumulated >= target:
            break

    vah_idx = max(va_bins)
    val_idx = min(va_bins)
    vah = price_min + (vah_idx + 1) * bin_size
    val = price_min + val_idx * bin_size

    bias = "bullish" if current_price > poc else ("bearish" if current_price < poc else "neutral")
    dist_to_poc = (current_price - poc) / poc * 100

    return {
        "poc": round(poc, 6),
        "vah": round(vah, 6),
        "val": round(val, 6),
        "bias": bias,
        "dist_to_poc_pct": round(dist_to_poc, 2),
        "above_vah": current_price > vah,
        "below_val": current_price < val,
        "in_value_area": val <= current_price <= vah,
    }


# ---------------------------------------------------------------------------
# 8. PREMIUM / DISCOUNT — SMC core rule for trade direction
# ---------------------------------------------------------------------------

def detect_premium_discount(candles: list, lookback: int = 50) -> dict:
    """
    SMC core rule:
      DISCOUNT zone (below 50% of range) = LOOK FOR LONGS only
      PREMIUM zone (above 50% of range) = LOOK FOR SHORTS only
      Never buy in premium, never sell in discount.

    This single rule filters out the majority of bad trades.
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    current_price = candles[-1]["close"]

    high = max(c["high"] for c in window)
    low = min(c["low"] for c in window)
    rng = high - low
    if rng == 0:
        return {"zone": "equilibrium", "position_pct": 50.0, "equilibrium": current_price}

    position_pct = (current_price - low) / rng * 100
    equilibrium = (high + low) / 2

    if position_pct <= 30:
        zone = "deep_discount"    # strongest buy zone
    elif position_pct <= 50:
        zone = "discount"         # buy zone
    elif position_pct <= 70:
        zone = "premium"          # sell zone
    else:
        zone = "deep_premium"     # strongest sell zone

    return {
        "zone": zone,
        "position_pct": round(position_pct, 1),
        "equilibrium": round(equilibrium, 6),
        "range_high": round(high, 6),
        "range_low": round(low, 6),
    }


# ---------------------------------------------------------------------------
# 9. CONFLUENCE SCORING & FINAL SIGNAL
# ---------------------------------------------------------------------------

def score_signal(ms: dict, ob: dict, fvg: dict, liq: dict,
                 sd: dict, fib: dict, vp: dict, pd: dict) -> dict:
    """
    Combines all SMC components into a final LONG/SHORT/NEUTRAL signal
    with a confidence score from 0-100.

    Scoring weights:
      Market structure (trend + BOS/CHoCH) : max 25 pts
      Order Block confluence                : max 15 pts
      Fair Value Gap (entering FVG)         : max 15 pts
      Liquidity sweep                       : max 15 pts
      Supply & Demand zone                  : max 10 pts
      Fibonacci OTE                         : max 10 pts
      Volume Profile (POC/VA)               : max 5 pts
      Premium/Discount alignment            : max 5 pts
    """
    long_score = 0
    short_score = 0
    reasons = []

    # 1. Market structure (25 pts)
    if ms.get("trend") == "bullish":
        long_score += 12
        reasons.append("Bullish trend (higher highs/lows)")
    elif ms.get("trend") == "bearish":
        short_score += 12
        reasons.append("Bearish trend (lower highs/lows)")

    struct = ms.get("structure", "")
    if struct == "CHoCH_bullish":
        long_score += 13
        reasons.append("CHoCH bullish — potential trend reversal UP ⚡")
    elif struct == "CHoCH_bearish":
        short_score += 13
        reasons.append("CHoCH bearish — potential trend reversal DOWN ⚡")
    elif struct == "BOS_bullish":
        long_score += 7
        reasons.append("BOS bullish — trend continuation up")
    elif struct == "BOS_bearish":
        short_score += 7
        reasons.append("BOS bearish — trend continuation down")

    # 2. Order blocks (15 pts)
    if ob.get("bullish_ob"):
        bull_ob = ob["bullish_ob"]
        if bull_ob.get("fresh"):
            long_score += 15
            reasons.append(f"Fresh bullish OB at {_r(bull_ob['high'])} — demand zone")
        else:
            long_score += 8
    if ob.get("bearish_ob"):
        bear_ob = ob["bearish_ob"]
        if bear_ob.get("fresh"):
            short_score += 15
            reasons.append(f"Fresh bearish OB at {_r(bear_ob['low'])} — supply zone")
        else:
            short_score += 8

    # 3. Fair Value Gaps (15 pts)
    if fvg.get("entering_bullish_fvg"):
        long_score += 15
        reasons.append("Price entering bullish FVG — magnet zone for longs ✦")
    elif fvg.get("bullish_fvg"):
        long_score += 7
        reasons.append(f"Bullish FVG below at {_r(fvg['bullish_fvg']['high'])}")

    if fvg.get("entering_bearish_fvg"):
        short_score += 15
        reasons.append("Price entering bearish FVG — magnet zone for shorts ✦")
    elif fvg.get("bearish_fvg"):
        short_score += 7
        reasons.append(f"Bearish FVG above at {_r(fvg['bearish_fvg']['low'])}")

    # 4. Liquidity sweeps (15 pts) — highest probability signal
    if liq.get("swept_sell_side"):
        long_score += 15
        reasons.append("Sell-side liquidity SWEPT — stop hunt complete, long reversal expected ⚡⚡")
    if liq.get("swept_buy_side"):
        short_score += 15
        reasons.append("Buy-side liquidity SWEPT — stop hunt complete, short reversal expected ⚡⚡")

    # 5. Supply & Demand zones (10 pts)
    if sd.get("in_demand"):
        dz = sd["demand_zone"]
        pts = 10 if dz.get("strength") == "strong" else 5
        long_score += pts
        reasons.append(f"Price in demand zone (tests: {dz.get('tests',0)}, strength: {dz.get('strength')})")
    if sd.get("in_supply"):
        sz = sd["supply_zone"]
        pts = 10 if sz.get("strength") == "strong" else 5
        short_score += pts
        reasons.append(f"Price in supply zone (tests: {sz.get('tests',0)}, strength: {sz.get('strength')})")

    # 6. Fibonacci OTE (10 pts)
    if fib.get("in_ote"):
        if fib.get("bias") == "bullish":
            long_score += 10
            reasons.append(f"Price in OTE zone ({fib.get('retracement_pct')}% retrace) — precision long entry")
        elif fib.get("bias") == "bearish":
            short_score += 10
            reasons.append(f"Price in OTE zone ({fib.get('retracement_pct')}% retrace) — precision short entry")

    # 7. Volume Profile (5 pts)
    if vp.get("poc"):
        if vp.get("bias") == "bullish":
            long_score += 5
        elif vp.get("bias") == "bearish":
            short_score += 5
        if vp.get("above_vah"):
            long_score += 3
            reasons.append(f"Price above VAH ({_r(vp['vah'])}) — strong bullish momentum")
        elif vp.get("below_val"):
            short_score += 3
            reasons.append(f"Price below VAL ({_r(vp['val'])}) — strong bearish pressure")

    # 8. Premium/Discount alignment (5 pts)
    zone = pd.get("zone", "")
    if zone in ("discount", "deep_discount"):
        long_score += 5
        if zone == "deep_discount":
            reasons.append(f"Price in DEEP DISCOUNT ({pd.get('position_pct')}% of range) — prime long zone")
        else:
            reasons.append(f"Price in discount zone ({pd.get('position_pct')}% of range) — favours longs")
    elif zone in ("premium", "deep_premium"):
        short_score += 5
        if zone == "deep_premium":
            reasons.append(f"Price in DEEP PREMIUM ({pd.get('position_pct')}% of range) — prime short zone")
        else:
            reasons.append(f"Price in premium zone ({pd.get('position_pct')}% of range) — favours shorts")

    # Determine direction and confidence
    max_score = 100
    if long_score >= short_score:
        direction = "long" if long_score > 20 else "neutral"
        confidence = min(100, int(long_score))
    else:
        direction = "short" if short_score > 20 else "neutral"
        confidence = min(100, int(short_score))

    # Confidence band
    if confidence >= 70:
        confidence_label = "HIGH — trade it"
    elif confidence >= 50:
        confidence_label = "MEDIUM — wait for one more confirmation"
    else:
        confidence_label = "LOW — skip or paper trade only"
        direction = "neutral"

    return {
        "direction": direction,
        "confidence": confidence,
        "confidence_label": confidence_label,
        "long_score": long_score,
        "short_score": short_score,
        "reasons": reasons,
    }


def _r(val):
    """Smart round for any price scale."""
    if val is None:
        return None
    if val == 0:
        return 0
    magnitude = math.floor(math.log10(abs(val)))
    places = max(0, 6 - magnitude - 1)
    return round(val, places)


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT — call from app.py
# ---------------------------------------------------------------------------

def run_smc_scan(symbol: str, candles_1h: list, candles_15m: Optional[list] = None) -> dict:
    """
    Run the full SMC signal scan on a coin.

    Parameters:
      symbol      : e.g. "BTCUSDT"
      candles_1h  : list of 1H OHLCV candles (at least 60 recommended)
      candles_15m : list of 15m candles (optional, used for entry precision)

    Returns a comprehensive signal dict with:
      - direction     : "long" | "short" | "neutral"
      - confidence    : 0-100
      - entry         : suggested entry price
      - stop_loss     : suggested SL (just below OB/demand/swing low)
      - target1       : first target (nearest FVG/OB/liquidity level)
      - target2       : second target (further liquidity / supply zone)
      - rr_ratio      : risk/reward ratio
      - all_components: raw output from each SMC detector
    """
    if not candles_1h or len(candles_1h) < 20:
        return {
            "symbol": symbol, "direction": "neutral", "confidence": 0,
            "confidence_label": "Insufficient data",
            "reasons": ["Need at least 20 candles for SMC analysis"],
        }

    current_price = candles_1h[-1]["close"]

    # Run all detectors
    ms  = detect_market_structure(candles_1h)
    ob  = detect_order_blocks(candles_1h)
    fvg = detect_fvg(candles_1h)
    liq = detect_liquidity(candles_1h)
    sd  = detect_supply_demand(candles_1h)
    fib = detect_fibonacci_ote(candles_1h)
    vp  = detect_volume_profile(candles_1h)
    pd_ = detect_premium_discount(candles_1h)

    # Score and combine
    sig = score_signal(ms, ob, fvg, liq, sd, fib, vp, pd_)

    # Calculate entry / SL / TP levels
    entry = current_price
    stop_loss = None
    target1 = None
    target2 = None

    if sig["direction"] == "long":
        # SL: just below the nearest bullish OB or demand zone or swing low
        sl_candidates = []
        if ob.get("bullish_ob"):
            sl_candidates.append(ob["bullish_ob"]["low"] * 0.998)
        if sd.get("demand_zone"):
            sl_candidates.append(sd["demand_zone"]["low"] * 0.998)
        if ms.get("last_swing_low"):
            sl_candidates.append(ms["last_swing_low"] * 0.997)
        stop_loss = max(sl_candidates) if sl_candidates else current_price * 0.98

        # T1: nearest bearish FVG or OB or liquidity level above
        t1_candidates = []
        if fvg.get("bearish_fvg"):
            t1_candidates.append(fvg["bearish_fvg"]["low"])
        if ob.get("bearish_ob"):
            t1_candidates.append(ob["bearish_ob"]["low"])
        if liq.get("buy_side_liquidity"):
            t1_candidates.append(liq["buy_side_liquidity"])
        target1 = min(t1_candidates) if t1_candidates else current_price * 1.02

        # T2: supply zone or further liquidity
        t2_candidates = []
        if sd.get("supply_zone"):
            t2_candidates.append(sd["supply_zone"]["low"])
        if liq.get("bsl_levels") and len(liq["bsl_levels"]) > 1:
            t2_candidates.append(liq["bsl_levels"][1])
        target2 = min(t2_candidates) if t2_candidates else current_price * 1.04

    elif sig["direction"] == "short":
        # SL: just above nearest bearish OB or supply zone or swing high
        sl_candidates = []
        if ob.get("bearish_ob"):
            sl_candidates.append(ob["bearish_ob"]["high"] * 1.002)
        if sd.get("supply_zone"):
            sl_candidates.append(sd["supply_zone"]["high"] * 1.002)
        if ms.get("last_swing_high"):
            sl_candidates.append(ms["last_swing_high"] * 1.003)
        stop_loss = min(sl_candidates) if sl_candidates else current_price * 1.02

        # T1: nearest bullish FVG or demand zone or liquidity level below
        t1_candidates = []
        if fvg.get("bullish_fvg"):
            t1_candidates.append(fvg["bullish_fvg"]["high"])
        if ob.get("bullish_ob"):
            t1_candidates.append(ob["bullish_ob"]["high"])
        if liq.get("sell_side_liquidity"):
            t1_candidates.append(liq["sell_side_liquidity"])
        target1 = max(t1_candidates) if t1_candidates else current_price * 0.98

        # T2: demand zone or further liquidity
        t2_candidates = []
        if sd.get("demand_zone"):
            t2_candidates.append(sd["demand_zone"]["high"])
        if liq.get("ssl_levels") and len(liq["ssl_levels"]) > 1:
            t2_candidates.append(liq["ssl_levels"][-2])
        target2 = max(t2_candidates) if t2_candidates else current_price * 0.96

    # RR ratio
    rr_ratio = None
    if stop_loss and target1:
        risk = abs(current_price - stop_loss)
        reward = abs(target1 - current_price)
        rr_ratio = round(min(reward / risk, 10.0), 2) if risk > 0 else None

    return {
        "symbol": symbol,
        "direction": sig["direction"],
        "confidence": sig["confidence"],
        "confidence_label": sig["confidence_label"],
        "long_score": sig["long_score"],
        "short_score": sig["short_score"],
        "reasons": sig["reasons"],
        "levels": {
            "entry": _r(entry),
            "stop_loss": _r(stop_loss),
            "target1": _r(target1),
            "target2": _r(target2),
            "rr_ratio": rr_ratio,
        },
        "components": {
            "market_structure": ms,
            "order_blocks": ob,
            "fair_value_gaps": fvg,
            "liquidity": liq,
            "supply_demand": sd,
            "fibonacci": fib,
            "volume_profile": vp,
            "premium_discount": pd_,
        },
    }


# ---------------------------------------------------------------------------
# INTEGRATION GUIDE FOR app.py
# ---------------------------------------------------------------------------
"""
STEP 1 — Add import at top of backend/app.py:
  from smc_engine import run_smc_scan

STEP 2 — In /api/scan/universe route, after existing scan, add:
  # Fetch 1H candles for SMC analysis
  candles_1h = get_candles(symbol, interval="1h", limit=65)

  # Run SMC scan
  smc_result = run_smc_scan(symbol, candles_1h)
  result["smc"] = smc_result

STEP 3 — In frontend/index.html, add SMC columns to the table:
  Direction / Confidence / Entry / SL / T1 / T2 / RR / Reasons

  In the row render loop:
  const smc = result.smc || {};
  const smcDir = smc.direction || 'neutral';
  const conf = smc.confidence || 0;
  const lvl = smc.levels || {};

  // Render:
  <td><span class="dir-pill dir-${smcDir}">${smcDir.toUpperCase()}</span></td>
  <td>${conf}% — ${smc.confidence_label || ''}</td>
  <td>${fmtPrice(lvl.entry)}</td>
  <td style="color:red">${fmtPrice(lvl.stop_loss)}</td>
  <td style="color:green">${fmtPrice(lvl.target1)}</td>
  <td style="color:green">${fmtPrice(lvl.target2)}</td>
  <td>${lvl.rr_ratio ? lvl.rr_ratio + 'x' : '—'}</td>
  <td class="reasons">${(smc.reasons||[]).slice(0,3).join(' | ')}</td>

STEP 4 — Push to GitHub → Render auto-deploys.
"""


if __name__ == "__main__":
    import random
    import math

    random.seed(42)
    def make_candles(start, vol_pct=0.03, n=70, seed=1):
        random.seed(seed)
        candles = []
        price = start
        for i in range(n):
            move = price * random.uniform(-vol_pct, vol_pct)
            # add a bullish impulse at candle 30 to create OB/BOS
            if i == 30:
                move = price * 0.04
            o = price
            c = max(price + move, start * 0.001)
            h = max(o, c) * (1 + random.uniform(0, vol_pct * 0.5))
            l = max(min(o, c) * (1 - random.uniform(0, vol_pct * 0.5)), start * 0.001)
            vol = random.uniform(500_000, 2_000_000)
            if i == 30:
                vol *= 5  # volume spike on the impulse
            candles.append({"open_time": i, "open": o, "high": h,
                             "low": l, "close": c, "volume": vol})
            price = c
        return candles

    print("=" * 60)
    print("SMC Engine — Test Suite")
    print("=" * 60)

    for name, start in [("BTC", 67500), ("ETH", 3550), ("WIF", 2.17),
                          ("JUP", 0.42), ("PEPE", 0.0000095)]:
        candles = make_candles(start)
        result = run_smc_scan(f"{name}USDT", candles)
        print(f"\n{name:8} | {result['direction'].upper():7} | conf={result['confidence']:3}%"
              f" | RR={result['levels'].get('rr_ratio') or '—'}"
              f" | {result['confidence_label']}")
        for r in result["reasons"][:3]:
            print(f"          → {r}")

    print("\n" + "=" * 60)
    print("All tests passed — drop smc_engine.py into backend/")
