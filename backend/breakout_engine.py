"""
breakout_engine.py  —  Multi-Timeframe Breakout + Retest Signal Engine
========================================================================
DROP INTO: backend/  alongside smc_engine.py and app.py

WHAT IT DOES
  Scans for high-probability breakout-retest setups across 4 timeframes:
    4H  → Major trend direction + key S/R level identification
    1H  → Breakout confirmation + retest zone validation
    15m → Entry confirmation (BOS after retest)
    5m  → Precise entry trigger

  Three signal types detected per coin:
    CONFIRMED_RETEST  — Breakout happened, retest is holding, enter now
    FRESH_BREAKOUT    — Just broke out, waiting for retest (set alert)
    FAKEOUT           — False breakout / stop hunt (trade the reversal)

SCORING (0–100, capped)
  4H breakout confirmed           +20   (major structure)
  1H retest holding               +20   (retest valid)
  15m BOS after retest            +15   (entry confirmed)
  5m  entry trigger               +10   (precise timing)
  Order Block at retest zone      +15   (SMC confluence)
  FVG at retest zone              +10   (SMC confluence)
  Liquidity sweep at retest       +10   (SMC confluence)
  Volume confirmation on breakout +10   (institutional participation)
  Max raw = 110, capped at 100

TARGETS
  Target1 = 1.5× risk (next swing high/S/R above for longs)
  Target2 = 2.5× risk (major structure level)
  Target3 = 4.0× risk (liquidity pool / supply zone)

CALLED BY: app.py → /api/scan/breakout
"""

import math
from typing import Optional


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _r(val):
    """Smart round for any price scale (BTC to PEPE)."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f) or f == 0:
        return f
    mag = math.floor(math.log10(abs(f)))
    return round(f, max(0, 6 - mag - 1))


def _pct(a, b):
    """Percentage difference: (a - b) / b * 100."""
    if not b:
        return 0.0
    return (a - b) / b * 100


def _candle_body(c):
    return abs(c["close"] - c["open"])


def _candle_range(c):
    return c["high"] - c["low"]


# ---------------------------------------------------------------------------
# 1. S/R Level Detection (from swing clusters)
# ---------------------------------------------------------------------------

def find_sr_levels(candles: list, lookback: int = 100,
                   swing_lookback: int = 3,
                   cluster_pct: float = 0.4) -> list:
    """
    Find key S/R levels from swing high/low clusters.
    Returns list of dicts: {price, strength, type}
    strength = number of times price touched this level (1-5+)
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    if len(window) < swing_lookback * 2 + 2:
        return []

    cur = candles[-1]["close"]
    tol = cur * (cluster_pct / 100)

    swing_prices = []
    n = len(window)
    for i in range(swing_lookback, n - swing_lookback):
        h = window[i]["high"]
        l = window[i]["low"]
        if all(window[i-j]["high"] <= h for j in range(1, swing_lookback+1)) and \
           all(window[i+j]["high"] <= h for j in range(1, swing_lookback+1)):
            swing_prices.append(h)
        if all(window[i-j]["low"] >= l for j in range(1, swing_lookback+1)) and \
           all(window[i+j]["low"] >= l for j in range(1, swing_lookback+1)):
            swing_prices.append(l)

    if not swing_prices:
        return []

    # Cluster nearby levels
    swing_prices.sort()
    clusters = []
    i = 0
    while i < len(swing_prices):
        group = [swing_prices[i]]
        j = i + 1
        while j < len(swing_prices) and swing_prices[j] - group[0] <= tol:
            group.append(swing_prices[j])
            j += 1
        price = sum(group) / len(group)
        strength = min(len(group), 5)
        level_type = "resistance" if price > cur else "support"
        clusters.append({"price": price, "strength": strength, "type": level_type})
        i = j

    return clusters


# ---------------------------------------------------------------------------
# 2. Trendline Detection
# ---------------------------------------------------------------------------

def find_trendline(candles: list, lookback: int = 50,
                   swing_lookback: int = 3) -> dict:
    """
    Detects the most recent dominant trendline (support or resistance).
    Uses linear regression on the last N swing highs (downtrend) or
    swing lows (uptrend).
    Returns {slope, intercept, type, r_squared, current_trendline_price}
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    n = len(window)
    if n < swing_lookback * 2 + 4:
        return {}

    swing_highs, swing_lows = [], []
    for i in range(swing_lookback, n - swing_lookback):
        h = window[i]["high"]
        l = window[i]["low"]
        if all(window[i-j]["high"] <= h for j in range(1, swing_lookback+1)) and \
           all(window[i+j]["high"] <= h for j in range(1, swing_lookback+1)):
            swing_highs.append((i, h))
        if all(window[i-j]["low"] >= l for j in range(1, swing_lookback+1)) and \
           all(window[i+j]["low"] >= l for j in range(1, swing_lookback+1)):
            swing_lows.append((i, l))

    def linreg(points):
        if len(points) < 2:
            return None
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        xm, ym = sum(xs)/len(xs), sum(ys)/len(ys)
        num = sum((x-xm)*(y-ym) for x,y in zip(xs,ys))
        den = sum((x-xm)**2 for x in xs)
        if den == 0:
            return None
        slope = num / den
        intercept = ym - slope * xm
        # R-squared
        ss_res = sum((y - (slope*x + intercept))**2 for x,y in zip(xs,ys))
        ss_tot = sum((y - ym)**2 for y in ys)
        r2 = 1 - ss_res/ss_tot if ss_tot > 0 else 0
        return {"slope": slope, "intercept": intercept, "r_squared": round(r2, 3)}

    cur_idx = n - 1
    result = {}

    # Try downtrend line (connecting swing highs — resistance trendline)
    if len(swing_highs) >= 2:
        reg = linreg(swing_highs[-4:])
        if reg and reg["r_squared"] > 0.7:
            tl_price = reg["slope"] * cur_idx + reg["intercept"]
            cur = candles[-1]["close"]
            result = {**reg, "type": "resistance_trendline",
                      "current_tl_price": _r(tl_price),
                      "dist_pct": round(_pct(cur, tl_price), 2)}

    # Try uptrend line (connecting swing lows — support trendline)
    if len(swing_lows) >= 2:
        reg = linreg(swing_lows[-4:])
        if reg and reg["r_squared"] > 0.7:
            tl_price = reg["slope"] * cur_idx + reg["intercept"]
            cur = candles[-1]["close"]
            # Take whichever trendline is closer and stronger
            if not result or abs(_pct(cur, tl_price)) < abs(result.get("dist_pct", 999)):
                result = {**reg, "type": "support_trendline",
                          "current_tl_price": _r(tl_price),
                          "dist_pct": round(_pct(cur, tl_price), 2)}

    return result


# ---------------------------------------------------------------------------
# 3. Breakout Detection per timeframe
# ---------------------------------------------------------------------------

def detect_breakout(candles: list, sr_levels: list,
                    trendline: dict, atr_mult: float = 0.3) -> dict:
    """
    Detects if price has broken out of a key level on this timeframe.
    A valid breakout requires:
      - Close beyond the level (not just a wick)
      - Body size > 0.3× ATR (not a doji)
      - The level had strength >= 2 (tested at least twice)

    Returns:
      broken_level   : the level that was broken
      direction      : "bullish" or "bearish"
      breakout_candle: the candle that broke out
      candles_ago    : how many candles ago the breakout happened
      valid          : True/False
    """
    if not candles or len(candles) < 10:
        return {"valid": False}

    # Simple ATR (14 period)
    atr_window = candles[-15:]
    trs = []
    for i in range(1, len(atr_window)):
        hi = atr_window[i]["high"]
        lo = atr_window[i]["low"]
        pc = atr_window[i-1]["close"]
        trs.append(max(hi-lo, abs(hi-pc), abs(lo-pc)))
    atr = sum(trs) / len(trs) if trs else candles[-1]["close"] * 0.01

    cur = candles[-1]["close"]

    # Check last 5 candles for a breakout
    for lookback in range(1, min(6, len(candles))):
        c = candles[-lookback]
        body = _candle_body(c)
        if body < atr * atr_mult:
            continue  # too small, skip

        # Check each S/R level
        for level in sr_levels:
            lp = level["price"]
            if level["strength"] < 2:
                continue

            # Bullish breakout: close above resistance
            if level["type"] == "resistance" and c["close"] > lp and \
               candles[-lookback-1]["close"] <= lp:
                return {
                    "valid": True, "direction": "bullish",
                    "broken_level": _r(lp), "level_strength": level["strength"],
                    "breakout_type": "sr_level",
                    "candles_ago": lookback,
                    "breakout_candle_high": _r(c["high"]),
                    "breakout_candle_close": _r(c["close"]),
                    "atr": _r(atr),
                }

            # Bearish breakout: close below support
            if level["type"] == "support" and c["close"] < lp and \
               candles[-lookback-1]["close"] >= lp:
                return {
                    "valid": True, "direction": "bearish",
                    "broken_level": _r(lp), "level_strength": level["strength"],
                    "breakout_type": "sr_level",
                    "candles_ago": lookback,
                    "breakout_candle_low": _r(c["low"]),
                    "breakout_candle_close": _r(c["close"]),
                    "atr": _r(atr),
                }

        # Trendline breakout
        if trendline.get("current_tl_price"):
            tlp = trendline["current_tl_price"]
            if trendline["type"] == "resistance_trendline" and \
               c["close"] > tlp and candles[-lookback-1]["close"] <= tlp:
                return {
                    "valid": True, "direction": "bullish",
                    "broken_level": _r(tlp), "level_strength": 3,
                    "breakout_type": "trendline",
                    "candles_ago": lookback,
                    "breakout_candle_close": _r(c["close"]),
                    "atr": _r(atr),
                }
            if trendline["type"] == "support_trendline" and \
               c["close"] < tlp and candles[-lookback-1]["close"] >= tlp:
                return {
                    "valid": True, "direction": "bearish",
                    "broken_level": _r(tlp), "level_strength": 3,
                    "breakout_type": "trendline",
                    "candles_ago": lookback,
                    "breakout_candle_close": _r(c["close"]),
                    "atr": _r(atr),
                }

    return {"valid": False}


# ---------------------------------------------------------------------------
# 4. Retest Detection
# ---------------------------------------------------------------------------

def detect_retest(candles: list, broken_level: float,
                  direction: str, atr: float) -> dict:
    """
    After a breakout, detects if price has pulled back to retest
    the broken level and is showing signs of holding.

    Retest is valid when:
      - Price pulled back to within 0.5× ATR of broken level
      - At least one candle closed back on the breakout side
      - The most recent candle shows rejection (wick toward level, body away)

    Returns:
      retested     : True/False
      holding      : True/False (price bounced off retest zone)
      retest_price : the price where retest occurred
      stage        : "confirmed" | "in_progress" | "none"
    """
    if not candles or not broken_level:
        return {"retested": False, "holding": False, "stage": "none"}

    tol = max(atr * 0.5, broken_level * 0.003)
    cur = candles[-1]["close"]

    # Check last 8 candles for a retest
    retested = False
    retest_price = None
    holding = False

    for i in range(1, min(9, len(candles))):
        c = candles[-i]
        low_touched  = abs(c["low"]  - broken_level) <= tol
        high_touched = abs(c["high"] - broken_level) <= tol
        close_touched = abs(c["close"] - broken_level) <= tol

        if direction == "bullish":
            # Bullish retest: price came back down to the broken resistance
            # (now acting as support) and closed back above
            if (low_touched or close_touched) and c["close"] >= broken_level * 0.998:
                retested = True
                retest_price = c["low"]
                # Holding: current price moving away from level upward
                if cur > broken_level * 1.002:
                    holding = True
                break
        else:
            # Bearish retest: price came back up to broken support
            # (now acting as resistance) and closed back below
            if (high_touched or close_touched) and c["close"] <= broken_level * 1.002:
                retested = True
                retest_price = c["high"]
                if cur < broken_level * 0.998:
                    holding = True
                break

    if retested and holding:
        stage = "confirmed"
    elif retested:
        stage = "in_progress"
    else:
        stage = "none"

    return {
        "retested": retested,
        "holding": holding,
        "retest_price": _r(retest_price),
        "stage": stage,
    }


# ---------------------------------------------------------------------------
# 5. Fakeout Detection
# ---------------------------------------------------------------------------

def detect_fakeout(candles: list, broken_level: float,
                   direction: str, atr: float) -> dict:
    """
    A fakeout (stop hunt / turtle soup) occurs when:
      - Price breaks a level (wick or close)
      - But snaps back quickly within 1-3 candles
      - Volume on the breakout candle is below average (thin breakout)
      - This signals a REVERSAL in the opposite direction

    This is one of the most profitable ICT setups.
    """
    if not candles or len(candles) < 5 or not broken_level:
        return {"is_fakeout": False}

    # Check last 3 candles for a snap-back
    last_3 = candles[-3:]
    cur = candles[-1]["close"]

    # Average volume for context
    avg_vol = sum(c.get("volume", 0) for c in candles[-20:]) / min(20, len(candles))

    for i, c in enumerate(last_3):
        broke_up = c["high"] > broken_level and c["close"] < broken_level
        broke_dn = c["low"]  < broken_level and c["close"] > broken_level

        if direction == "bullish" and broke_up:
            vol_thin = c.get("volume", avg_vol) < avg_vol * 0.8
            return {
                "is_fakeout": True,
                "fakeout_direction": "bearish",  # fake bullish breakout → go short
                "fakeout_candle_close": _r(c["close"]),
                "snap_back_confirmed": cur < broken_level,
                "volume_thin": vol_thin,
                "note": "False breakout above resistance — stop hunt. SHORT opportunity.",
            }

        if direction == "bearish" and broke_dn:
            vol_thin = c.get("volume", avg_vol) < avg_vol * 0.8
            return {
                "is_fakeout": True,
                "fakeout_direction": "bullish",  # fake bearish breakout → go long
                "fakeout_candle_close": _r(c["close"]),
                "snap_back_confirmed": cur > broken_level,
                "volume_thin": vol_thin,
                "note": "False breakdown below support — stop hunt. LONG opportunity.",
            }

    return {"is_fakeout": False}


# ---------------------------------------------------------------------------
# 6. SMC Confluence Check at retest zone
# ---------------------------------------------------------------------------

def check_smc_confluence(candles: list, zone_price: float,
                          zone_tolerance_pct: float = 0.5) -> dict:
    """
    Checks if an SMC concept aligns with the retest zone:
      - Order Block within zone_tolerance_pct of zone_price
      - FVG overlapping the zone
      - Liquidity sweep just before the retest

    Each confluence adds to the breakout score.
    """
    if not candles or not zone_price:
        return {"ob": False, "fvg": False, "liq_sweep": False, "total": 0}

    cur = candles[-1]["close"]
    tol = zone_price * (zone_tolerance_pct / 100)
    window = candles[-60:] if len(candles) > 60 else candles

    ob_at_zone  = False
    fvg_at_zone = False
    liq_sweep   = False

    # Order Block check
    for i in range(1, len(window) - 1):
        c = window[i]
        cn = window[i+1]
        body = abs(c["close"] - c["open"])
        if body < cur * 0.0001:
            continue
        if c["close"] < c["open"]:  # bearish candle → bullish OB
            move_up = _pct(cn["high"], c["low"])
            if move_up >= 0.8 and abs(c["high"] - zone_price) <= tol:
                ob_at_zone = True
        elif c["close"] > c["open"]:  # bullish candle → bearish OB
            move_dn = _pct(c["high"], cn["low"])
            if move_dn >= 0.8 and abs(c["low"] - zone_price) <= tol:
                ob_at_zone = True

    # FVG check
    for i in range(1, len(window) - 1):
        cp = window[i-1]; cn = window[i+1]
        if cp["high"] < cn["low"]:
            fvg_lo, fvg_hi = cp["high"], cn["low"]
            if fvg_lo <= zone_price <= fvg_hi:
                fvg_at_zone = True
        elif cp["low"] > cn["high"]:
            fvg_lo, fvg_hi = cn["high"], cp["low"]
            if fvg_lo <= zone_price <= fvg_hi:
                fvg_at_zone = True

    # Liquidity sweep: wick beyond zone_price then close back
    last = candles[-1]
    prev = candles[-2] if len(candles) >= 2 else last
    if last["low"] < zone_price < last["close"]:
        liq_sweep = True
    if last["high"] > zone_price > last["close"]:
        liq_sweep = True

    total = (15 if ob_at_zone else 0) + (10 if fvg_at_zone else 0) + (10 if liq_sweep else 0)
    return {"ob": ob_at_zone, "fvg": fvg_at_zone, "liq_sweep": liq_sweep, "total": total}


# ---------------------------------------------------------------------------
# 7. Volume Confirmation
# ---------------------------------------------------------------------------

def check_volume_confirmation(candles: list, breakout_candle_idx: int = -2) -> dict:
    """
    Validates that the breakout candle had above-average volume.
    Institutional breakouts have HIGH volume. Retail traps have thin volume.
    """
    if not candles or len(candles) < 10:
        return {"confirmed": False, "ratio": None}

    avg_vol = sum(c.get("volume", 0) for c in candles[-20:]) / min(20, len(candles))
    bk_vol  = candles[breakout_candle_idx].get("volume", 0) if abs(breakout_candle_idx) <= len(candles) else 0

    if avg_vol == 0:
        return {"confirmed": False, "ratio": None}

    ratio = bk_vol / avg_vol
    return {
        "confirmed": ratio >= 1.3,  # 30% above average = institutional
        "ratio": round(ratio, 2),
        "note": "High volume breakout — institutional" if ratio >= 1.3
                else "Low volume breakout — caution, possible fakeout",
    }


# ---------------------------------------------------------------------------
# 8. Entry / SL / Targets
# ---------------------------------------------------------------------------

def calc_levels(direction: str, cur: float, broken_level: float,
                retest_price: float, atr: float,
                sr_levels: list) -> dict:
    """
    Entry  = current price (or retest level for limit orders)
    SL     = just below retest low (long) or above retest high (short)
    T1     = 1.5 × risk
    T2     = 2.5 × risk
    T3     = 4.0 × risk (liquidity pool / major S/R)

    For confirmed retests, entry is at current price.
    Limit entry = retest_price ± small buffer.
    """
    if not atr:
        atr = cur * 0.01

    entry = cur
    limit_entry = None
    sl = tp1 = tp2 = tp3 = None

    if direction == "bullish":
        # SL just below the retest zone / broken level
        sl_base = min(retest_price or broken_level, broken_level) if retest_price else broken_level
        sl = min(sl_base * 0.997, entry - atr * 0.3)
        limit_entry = (retest_price or broken_level) * 1.001

        risk = entry - sl
        if risk <= 0:
            risk = atr * 0.5

        tp1 = entry + risk * 1.5
        tp2 = entry + risk * 2.5
        tp3 = entry + risk * 4.0

        # Snap T3 to nearest resistance above if available
        resistances = [l["price"] for l in sr_levels
                       if l["type"] == "resistance" and l["price"] > tp2]
        if resistances:
            tp3 = min(resistances)

    else:  # bearish
        sl_base = max(retest_price or broken_level, broken_level) if retest_price else broken_level
        sl = max(sl_base * 1.003, entry + atr * 0.3)
        limit_entry = (retest_price or broken_level) * 0.999

        risk = sl - entry
        if risk <= 0:
            risk = atr * 0.5

        tp1 = entry - risk * 1.5
        tp2 = entry - risk * 2.5
        tp3 = entry - risk * 4.0

        supports = [l["price"] for l in sr_levels
                    if l["type"] == "support" and l["price"] < tp2]
        if supports:
            tp3 = max(supports)

    rr1 = round(min(abs(tp1 - entry) / abs(entry - sl), 10.0), 2) if sl and tp1 and entry != sl else None
    rr2 = round(min(abs(tp2 - entry) / abs(entry - sl), 10.0), 2) if sl and tp2 and entry != sl else None
    rr3 = round(min(abs(tp3 - entry) / abs(entry - sl), 10.0), 2) if sl and tp3 and entry != sl else None

    return {
        "entry":       _r(entry),
        "limit_entry": _r(limit_entry),
        "stop_loss":   _r(sl),
        "target1":     _r(tp1),
        "target2":     _r(tp2),
        "target3":     _r(tp3),
        "rr1": rr1, "rr2": rr2, "rr3": rr3,
    }


# ---------------------------------------------------------------------------
# 9. Multi-Timeframe Score Assembly
# ---------------------------------------------------------------------------

def assemble_score(tf4h: dict, tf1h: dict, tf15m: dict, tf5m: dict,
                   smc: dict, vol: dict, fakeout: dict) -> dict:
    """
    Combines all timeframe signals into a final score and signal type.
    """
    score = 0
    reasons = []
    signal_type = "NO_SIGNAL"
    direction = "neutral"

    # Fakeout overrides everything — highest conviction reversal
    if fakeout.get("is_fakeout"):
        direction = fakeout.get("fakeout_direction", "neutral")
        score = 75 if fakeout.get("snap_back_confirmed") else 55
        if fakeout.get("volume_thin"):
            score += 10
        signal_type = "FAKEOUT"
        reasons.append(fakeout.get("note", "Fakeout detected"))
        reasons.append(f"Trade direction: {direction.upper()}")
        return {"score": min(score, 100), "signal_type": signal_type,
                "direction": direction, "reasons": reasons}

    # Need at least 4H breakout to continue
    bo4h = tf4h.get("breakout", {})
    if not bo4h.get("valid"):
        return {"score": 0, "signal_type": "NO_SIGNAL",
                "direction": "neutral", "reasons": ["No 4H breakout found"]}

    direction = bo4h["direction"]

    # 4H breakout (20 pts)
    score += 20
    reasons.append(f"4H {bo4h['breakout_type'].replace('_',' ')} breakout "
                   f"({'bullish ↑' if direction=='bullish' else 'bearish ↓'}) "
                   f"at {bo4h.get('broken_level')} "
                   f"(str {bo4h.get('level_strength','?')}/5, "
                   f"{bo4h.get('candles_ago',0)} candles ago)")

    # 1H retest (20 pts)
    rt1h = tf1h.get("retest", {})
    if rt1h.get("stage") == "confirmed":
        score += 20
        reasons.append(f"1H retest CONFIRMED at {rt1h.get('retest_price')} ✓")
        signal_type = "CONFIRMED_RETEST"
    elif rt1h.get("retested"):
        score += 10
        reasons.append(f"1H retest in progress at {rt1h.get('retest_price')}")
        signal_type = "CONFIRMED_RETEST"
    else:
        reasons.append("1H retest not yet — watching for pullback")
        signal_type = "FRESH_BREAKOUT"

    # 15m BOS after retest (15 pts)
    bo15m = tf15m.get("breakout", {})
    if bo15m.get("valid") and bo15m.get("direction") == direction:
        score += 15
        reasons.append(f"15m BOS confirms continuation {direction} ✓")
    elif signal_type == "CONFIRMED_RETEST":
        reasons.append("15m BOS not yet — wait for 15m confirmation before entry")

    # 5m entry trigger (10 pts)
    bo5m = tf5m.get("breakout", {})
    if bo5m.get("valid") and bo5m.get("direction") == direction:
        score += 10
        reasons.append("5m entry trigger fired ✓ — highest precision entry")
    elif signal_type == "CONFIRMED_RETEST":
        reasons.append("5m trigger pending — use limit order at retest zone")

    # SMC confluence (up to 35 pts)
    smc_pts = smc.get("total", 0)
    score += smc_pts
    if smc.get("ob"):
        reasons.append("Order Block at retest zone ✦")
    if smc.get("fvg"):
        reasons.append("Fair Value Gap overlapping retest zone ✦")
    if smc.get("liq_sweep"):
        reasons.append("Liquidity sweep at retest — stop hunt complete ⚡")

    # Volume (10 pts)
    if vol.get("confirmed"):
        score += 10
        reasons.append(f"Volume confirmation {vol.get('ratio',0):.1f}× avg ✓")
    else:
        reasons.append(f"Volume {vol.get('ratio',0):.1f}× avg — thin breakout, caution")

    # Confidence label
    score = min(score, 100)
    if score >= 80:
        label = "STRONG — high probability setup"
    elif score >= 60:
        label = "MODERATE — valid setup, confirm on 5m"
    elif score >= 40:
        label = "WATCH — early stage, not ready to trade"
    else:
        label = "WEAK — skip"
        signal_type = "NO_SIGNAL"

    return {
        "score": score,
        "signal_type": signal_type,
        "direction": direction,
        "confidence_label": label,
        "reasons": reasons,
    }


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------

def run_breakout_scan(symbol: str,
                      candles_4h: list,
                      candles_1h: list,
                      candles_15m: list,
                      candles_5m: list) -> dict:
    """
    Full multi-timeframe breakout + retest scan for one coin.

    Parameters
    ----------
    symbol      : e.g. "BTCUSDT"
    candles_4h  : 4H OHLCV candles (100+ recommended)
    candles_1h  : 1H OHLCV candles (100+ recommended)
    candles_15m : 15m OHLCV candles (100+ recommended)
    candles_5m  : 5m OHLCV candles (60+ recommended)

    Returns
    -------
    dict with:
      symbol, score, signal_type, direction, confidence_label,
      entry, stop_loss, target1, target2, target3,
      rr1, rr2, rr3, reasons, timeframe_detail
    """
    empty = {
        "symbol": symbol, "score": 0, "signal_type": "NO_SIGNAL",
        "direction": "neutral", "confidence_label": "Insufficient data",
        "reasons": [], "levels": {}, "timeframe_detail": {},
    }

    if not candles_4h or len(candles_4h) < 20:
        return empty

    cur = candles_4h[-1]["close"] if candles_4h else 0

    # ── Step 1: Build S/R levels from 4H (most reliable) ──────────────────
    sr_levels_4h = find_sr_levels(candles_4h, lookback=120)
    trendline_4h = find_trendline(candles_4h, lookback=80)

    # ── Step 2: Detect breakout on each timeframe ──────────────────────────
    bo4h  = detect_breakout(candles_4h,  sr_levels_4h, trendline_4h)
    bo1h  = detect_breakout(candles_1h,  sr_levels_4h, trendline_4h) if candles_1h else {"valid": False}
    bo15m = detect_breakout(candles_15m, sr_levels_4h, trendline_4h) if candles_15m else {"valid": False}
    bo5m  = detect_breakout(candles_5m,  sr_levels_4h, trendline_4h) if candles_5m else {"valid": False}

    # ── Step 3: Detect retest on 1H ───────────────────────────────────────
    rt1h = {}
    fakeout = {"is_fakeout": False}
    if bo4h.get("valid"):
        bl  = bo4h.get("broken_level", 0)
        atr = bo4h.get("atr", cur * 0.01) or cur * 0.01
        rt1h    = detect_retest(candles_1h or candles_4h, bl, bo4h["direction"], atr)
        fakeout = detect_fakeout(candles_1h or candles_4h, bl, bo4h["direction"], atr)

    # ── Step 4: SMC confluence at the retest zone ─────────────────────────
    zone = bo4h.get("broken_level") or (rt1h.get("retest_price") if rt1h else None)
    smc  = check_smc_confluence(candles_1h or candles_4h, zone) if zone else {"total": 0}

    # ── Step 5: Volume confirmation ────────────────────────────────────────
    bo_candle_ago = bo4h.get("candles_ago", 1)
    vol_candle_idx = -(bo_candle_ago)
    vol = check_volume_confirmation(candles_4h, vol_candle_idx)

    # ── Step 6: Score assembly ─────────────────────────────────────────────
    tf4h_data  = {"breakout": bo4h}
    tf1h_data  = {"breakout": bo1h,  "retest": rt1h}
    tf15m_data = {"breakout": bo15m}
    tf5m_data  = {"breakout": bo5m}

    result = assemble_score(tf4h_data, tf1h_data, tf15m_data,
                            tf5m_data, smc, vol, fakeout)

    # ── Step 7: Calculate levels ───────────────────────────────────────────
    levels = {}
    if result["signal_type"] != "NO_SIGNAL" and bo4h.get("valid"):
        atr = bo4h.get("atr", cur * 0.01) or cur * 0.01
        levels = calc_levels(
            direction=result["direction"],
            cur=cur,
            broken_level=bo4h.get("broken_level", cur),
            retest_price=rt1h.get("retest_price") if rt1h else None,
            atr=atr,
            sr_levels=sr_levels_4h,
        )

    return {
        "symbol":           symbol,
        "current_price":    _r(cur),
        "score":            result["score"],
        "signal_type":      result["signal_type"],
        "direction":        result["direction"],
        "confidence_label": result.get("confidence_label", ""),
        "reasons":          result["reasons"],
        "levels":           levels,
        "smc_confluence":   smc,
        "volume":           vol,
        "timeframe_detail": {
            "4H":  {"breakout": bo4h,  "trendline": trendline_4h},
            "1H":  {"breakout": bo1h,  "retest": rt1h},
            "15m": {"breakout": bo15m},
            "5m":  {"breakout": bo5m},
            "fakeout": fakeout,
        },
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random

    def make_candles(start, n=120, vol=0.02, seed=1, trend="up"):
        random.seed(seed)
        out, price = [], start
        for i in range(n):
            drift = price * 0.003 if trend == "up" else -price * 0.002
            mv = drift + price * random.uniform(-vol, vol)
            # Create a clear breakout at candle 80
            if i == 80:
                mv = price * 0.04 if trend == "up" else -price * 0.04
            # Create a retest at candle 90
            if i == 90:
                mv = -price * 0.015 if trend == "up" else price * 0.015
            o = price
            c = max(o + mv, start * 0.001)
            h = max(o, c) * (1 + random.uniform(0, vol * 0.5))
            l = max(min(o, c) * (1 - random.uniform(0, vol * 0.5)), start * 0.001)
            out.append({"open_time": i, "open": o, "high": h,
                        "low": l, "close": c,
                        "volume": random.uniform(1e6, 5e6) * (3 if i == 80 else 1)})
            price = c
        return out

    print("Breakout Engine — Self Test")
    print("=" * 60)
    tests = [
        ("BTC",  67500, 1, "up"),
        ("ETH",  3550,  2, "up"),
        ("SOL",  165,   3, "down"),
        ("XRP",  2.15,  4, "up"),
        ("PEPE", 0.0000095, 5, "down"),
    ]
    for name, start, seed, trend in tests:
        c4h  = make_candles(start, n=120, seed=seed,   trend=trend)
        c1h  = make_candles(start, n=100, seed=seed+1, trend=trend)
        c15m = make_candles(start, n=80,  seed=seed+2, vol=0.015, trend=trend)
        c5m  = make_candles(start, n=60,  seed=seed+3, vol=0.01,  trend=trend)
        r = run_breakout_scan(f"{name}USDT", c4h, c1h, c15m, c5m)
        print(f"{name:6} | {r['signal_type']:20} | score={r['score']:3} "
              f"| dir={r['direction']:8} | {r['confidence_label']}")
        if r["levels"]:
            lv = r["levels"]
            print(f"       entry={lv.get('entry')} SL={lv.get('stop_loss')} "
                  f"T1={lv.get('target1')} T2={lv.get('target2')} T3={lv.get('target3')}")
            print(f"       RR: T1={lv.get('rr1')}x T2={lv.get('rr2')}x T3={lv.get('rr3')}x")
        print(f"       {r['reasons'][0] if r['reasons'] else ''}")
    print("=" * 60)
    print("Done")
