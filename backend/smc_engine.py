"""
smc_engine.py  —  Smart Money Concepts Signal Engine (Screener Edition)
========================================================================
PURPOSE: Morning screener across 118 coins. 15m candles. Top-20 output.
         NOT for algo trading — for deciding which coins to WATCH today.

CONCEPTS IMPLEMENTED
  1. Market Structure  — BOS (Break of Structure), CHoCH (Change of Character)
  2. Order Blocks      — Last bearish candle before bullish impulse (and vice versa)
  3. Fair Value Gaps   — 3-candle imbalance zones price is attracted back to
  4. Liquidity Sweeps  — Equal highs/lows hunted by big players before reversal
  5. Supply & Demand   — Origin zones of strong impulsive moves
  6. Fibonacci OTE     — Optimal Trade Entry at 62–79% retracement
  7. Volume Profile    — POC, VAH, VAL from recent bars
  8. Premium/Discount  — Price position in range (core SMC rule: buy discount, sell premium)
  9. Session Kill Zones— Asia / London / New York windows (ICT concept)
                         Best SMC signals fire during active kill zones

CONFIDENCE SCORING  (0–100)
  ≥ 70  HIGH   — strong confluence, consider taking the trade
  50–69 MEDIUM — valid setup, wait for one more confirmation
  < 50  LOW    — skip, paper trade only

ENTRY / SL / TARGET LOGIC
  Entry   = current price (market order) or nearest OB/FVG edge (limit)
  SL      = just below nearest bullish OB or swing low (long)
            just above nearest bearish OB or swing high (short)
  Target1 = nearest opposing FVG or OB or liquidity level (~1–2% move)
  Target2 = next liquidity pool or supply/demand zone (~2–4% move)

DROP INTO: backend/  alongside app.py
CALLED BY: app.py → /api/scan/smc endpoint
"""

import math
import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Session Kill Zones (IST = UTC+5:30)
# Big players execute during these windows — signals have higher follow-through
# ---------------------------------------------------------------------------
KILL_ZONES_UTC = {
    "Asia":     (23, 2),    # 23:00–02:00 UTC  →  04:30–07:30 IST
    "London":   (7,  10),   # 07:00–10:00 UTC  →  12:30–15:30 IST
    "New York": (13, 16),   # 13:00–16:00 UTC  →  18:30–21:30 IST
}

def current_kill_zone() -> Optional[str]:
    """Returns name of active kill zone or None."""
    h = datetime.datetime.now(datetime.timezone.utc).hour
    for name, (start, end) in KILL_ZONES_UTC.items():
        if start <= end:
            if start <= h < end:
                return name
        else:  # wraps midnight
            if h >= start or h < end:
                return name
    return None

def kill_zone_bias(zone: Optional[str]) -> str:
    """
    Each kill zone has a typical institutional bias:
      Asia    — accumulation / manipulation (traps retail)
      London  — strong directional moves, trend initiation
      New York— continuation or reversal of London trend, highest volume
    """
    biases = {
        "Asia":     "Accumulation — watch for liquidity sweeps, wait for London",
        "London":   "High probability — strongest directional moves of the day",
        "New York": "Continuation or reversal — confirm London trend or CHoCH",
    }
    return biases.get(zone, "Off-session — lower probability, wider spreads")


# ---------------------------------------------------------------------------
# 1. Market Structure — BOS & CHoCH
# ---------------------------------------------------------------------------
def detect_swing_points(candles: list, lookback: int = 3):
    highs, lows = [], []
    n = len(candles)
    for i in range(lookback, n - lookback):
        h, l = candles[i]["high"], candles[i]["low"]
        if all(candles[i-j]["high"] <= h for j in range(1, lookback+1)) and \
           all(candles[i+j]["high"] <= h for j in range(1, lookback+1)):
            highs.append((i, h))
        if all(candles[i-j]["low"] >= l for j in range(1, lookback+1)) and \
           all(candles[i+j]["low"] >= l for j in range(1, lookback+1)):
            lows.append((i, l))
    return {"highs": highs, "lows": lows}


def detect_market_structure(candles: list) -> dict:
    if len(candles) < 20:
        return {"trend": "ranging", "structure": "none", "choch": False,
                "last_swing_high": None, "last_swing_low": None}

    swings = detect_swing_points(candles[:-1], lookback=3)
    cur_high = candles[-1]["high"]
    cur_low  = candles[-1]["low"]

    rh = swings["highs"][-3:]
    rl = swings["lows"][-3:]

    last_sh  = rh[-1][1] if rh else None
    last_sl  = rl[-1][1] if rl else None
    prev_sh  = rh[-2][1] if len(rh) >= 2 else None
    prev_sl  = rl[-2][1] if len(rl) >= 2 else None

    if last_sh and prev_sh and last_sl and prev_sl:
        if last_sh > prev_sh and last_sl > prev_sl:
            trend = "bullish"
        elif last_sh < prev_sh and last_sl < prev_sl:
            trend = "bearish"
        else:
            trend = "ranging"
    else:
        trend = "ranging"

    structure, choch = "none", False
    if last_sh and cur_high > last_sh:
        if trend == "bullish":
            structure = "BOS_bullish"
        else:
            structure = "CHoCH_bullish"; choch = True
    elif last_sl and cur_low < last_sl:
        if trend == "bearish":
            structure = "BOS_bearish"
        else:
            structure = "CHoCH_bearish"; choch = True

    return {"trend": trend, "structure": structure, "choch": choch,
            "last_swing_high": last_sh, "last_swing_low": last_sl}


# ---------------------------------------------------------------------------
# 2. Order Blocks
# ---------------------------------------------------------------------------
def detect_order_blocks(candles: list, lookback: int = 60,
                         min_move_pct: float = 0.8) -> dict:
    window = candles[-lookback:] if len(candles) > lookback else candles
    cur = candles[-1]["close"]
    bull_obs, bear_obs = [], []

    for i in range(1, len(window) - 1):
        c, cn = window[i], window[i+1]
        body = abs(c["close"] - c["open"])
        if body < cur * 0.0001:
            continue
        if c["close"] < c["open"]:   # bearish candle
            move_up = (cn["high"] - c["low"]) / max(c["low"], 1e-12) * 100
            if move_up >= min_move_pct:
                fresh = cur > c["high"]
                bull_obs.append({"high": c["high"], "low": c["low"],
                                  "mid": (c["high"]+c["low"])/2,
                                  "fresh": fresh, "index": i})
        elif c["close"] > c["open"]: # bullish candle
            move_dn = (c["high"] - cn["low"]) / max(c["high"], 1e-12) * 100
            if move_dn >= min_move_pct:
                fresh = cur < c["low"]
                bear_obs.append({"high": c["high"], "low": c["low"],
                                   "mid": (c["high"]+c["low"])/2,
                                   "fresh": fresh, "index": i})

    fresh_bull = [o for o in bull_obs if o["fresh"] and o["high"] < cur]
    fresh_bear = [o for o in bear_obs if o["fresh"] and o["low"]  > cur]
    nb = max(fresh_bull, key=lambda x: x["high"]) if fresh_bull else None
    sb = min(fresh_bear, key=lambda x: x["low"])  if fresh_bear else None

    # Check if price is currently inside an OB (highest-quality entry zone)
    in_bull_ob = nb and nb["low"] <= cur <= nb["high"]
    in_bear_ob = sb and sb["low"] <= cur <= sb["high"]

    return {"bullish_ob": nb, "bearish_ob": sb,
            "in_bullish_ob": in_bull_ob, "in_bearish_ob": in_bear_ob}


# ---------------------------------------------------------------------------
# 3. Fair Value Gaps
# ---------------------------------------------------------------------------
def detect_fvg(candles: list, lookback: int = 40) -> dict:
    window = candles[-lookback:] if len(candles) > lookback else candles
    cur = candles[-1]["close"]
    bull_fvgs, bear_fvgs = [], []

    for i in range(1, len(window) - 1):
        cp, cn = window[i-1], window[i+1]
        if cp["high"] < cn["low"]:
            hi, lo = cn["low"], cp["high"]
            if (hi - lo) / max(lo, 1e-12) * 100 >= 0.05:
                filled = cur < lo
                bull_fvgs.append({"high": hi, "low": lo, "mid": (hi+lo)/2,
                                   "filled": filled, "index": i})
        elif cp["low"] > cn["high"]:
            hi, lo = cp["low"], cn["high"]
            if (hi - lo) / max(lo, 1e-12) * 100 >= 0.05:
                filled = cur > hi
                bear_fvgs.append({"high": hi, "low": lo, "mid": (hi+lo)/2,
                                   "filled": filled, "index": i})

    fb = [f for f in bull_fvgs if not f["filled"] and f["high"] < cur]
    sb = [f for f in bear_fvgs if not f["filled"] and f["low"]  > cur]
    nb = max(fb, key=lambda x: x["high"]) if fb else None
    sb2 = min(sb, key=lambda x: x["low"]) if sb else None

    entering_bull = nb  and nb["low"]  <= cur <= nb["high"]
    entering_bear = sb2 and sb2["low"] <= cur <= sb2["high"]

    return {"bullish_fvg": nb, "bearish_fvg": sb2,
            "entering_bullish_fvg": entering_bull,
            "entering_bearish_fvg": entering_bear}


# ---------------------------------------------------------------------------
# 4. Liquidity Sweeps
# ---------------------------------------------------------------------------
def detect_liquidity(candles: list, lookback: int = 50,
                      tolerance_pct: float = 0.2) -> dict:
    """
    Equal highs above = buy-side liquidity (BSL) — stops of shorts
    Equal lows below  = sell-side liquidity (SSL) — stops of longs

    A SWEEP = last candle wicked through a liquidity level but closed back.
    This is the highest-probability reversal signal in SMC:
      Sweep of SSL + close back above → LONG (stops hunted, reversal up)
      Sweep of BSL + close back below → SHORT (stops hunted, reversal down)
    """
    window = candles[-lookback:] if len(candles) > lookback else candles
    last   = candles[-1]
    cur    = last["close"]
    tol    = cur * (tolerance_pct / 100)

    hs = [c["high"] for c in window[:-1]]
    ls = [c["low"]  for c in window[:-1]]

    # Find equal highs (multiple candles touching same level)
    bsl_levels = []
    for h in set(round(x / tol) * tol for x in hs):
        count = sum(1 for x in hs if abs(x - h) <= tol)
        if count >= 2:
            bsl_levels.append(h)

    ssl_levels = []
    for l in set(round(x / tol) * tol for x in ls):
        count = sum(1 for x in ls if abs(x - l) <= tol)
        if count >= 2:
            ssl_levels.append(l)

    bsl_above = sorted([h for h in bsl_levels if h > cur * 1.001])
    ssl_below = sorted([l for l in ssl_levels if l < cur * 0.999], reverse=True)

    nearest_bsl = bsl_above[0]  if bsl_above else None
    nearest_ssl = ssl_below[0]  if ssl_below else None

    # Detect active sweep on the last candle
    swept_ssl = False  # wick below SSL, closed above → long signal
    swept_bsl = False  # wick above BSL, closed below → short signal
    for level in ssl_below:
        if last["low"] < level < last["close"]:
            swept_ssl = True
    for level in bsl_above:
        if last["high"] > level > last["close"]:
            swept_bsl = True

    dist_bsl = (nearest_bsl - cur) / cur * 100 if nearest_bsl else None
    dist_ssl = (cur - nearest_ssl) / cur * 100 if nearest_ssl else None

    return {
        "buy_side_liquidity":  nearest_bsl,
        "sell_side_liquidity": nearest_ssl,
        "swept_sell_side":     swept_ssl,   # bullish signal
        "swept_buy_side":      swept_bsl,   # bearish signal
        "dist_to_bsl_pct":     round(dist_bsl, 2) if dist_bsl else None,
        "dist_to_ssl_pct":     round(dist_ssl, 2) if dist_ssl else None,
        "bsl_count":           len(bsl_above),
        "ssl_count":           len(ssl_below),
    }


# ---------------------------------------------------------------------------
# 5. Supply & Demand Zones
# ---------------------------------------------------------------------------
def detect_supply_demand(candles: list, lookback: int = 80,
                          min_move_pct: float = 1.2) -> dict:
    window = candles[-lookback:] if len(candles) > lookback else candles
    cur = candles[-1]["close"]
    demand_zones, supply_zones = [], []

    for i in range(2, len(window) - 2):
        base_lo = min(window[i-1]["low"], window[i-2]["low"])
        base_hi = max(window[i-1]["high"], window[i]["open"])
        move_up = (window[i]["high"] - base_lo) / max(base_lo, 1e-12) * 100
        if move_up >= min_move_pct:
            tests   = sum(1 for c in window[i+1:] if base_lo <= c["low"] <= base_hi)
            demand_zones.append({"high": base_hi, "low": base_lo,
                                   "mid": (base_hi+base_lo)/2, "tests": tests,
                                   "fresh": cur > base_hi, "index": i})

        base_hi2 = max(window[i-1]["high"], window[i-2]["high"])
        base_lo2 = min(window[i-1]["low"],  window[i]["open"])
        move_dn  = (base_hi2 - window[i]["low"]) / max(base_hi2, 1e-12) * 100
        if move_dn >= min_move_pct:
            tests    = sum(1 for c in window[i+1:] if base_lo2 <= c["high"] <= base_hi2)
            supply_zones.append({"high": base_hi2, "low": base_lo2,
                                    "mid": (base_hi2+base_lo2)/2, "tests": tests,
                                    "fresh": cur < base_lo2, "index": i})

    fd = [z for z in demand_zones if z["fresh"] and z["high"] < cur]
    fs = [z for z in supply_zones if z["fresh"] and z["low"]  > cur]
    nd = max(fd, key=lambda x: x["high"]) if fd else None
    ns = min(fs, key=lambda x: x["low"])  if fs else None

    return {"demand_zone": nd, "supply_zone": ns,
            "in_demand": nd and nd["low"] <= cur <= nd["high"],
            "in_supply": ns and ns["low"] <= cur <= ns["high"]}


# ---------------------------------------------------------------------------
# 6. Fibonacci OTE
# ---------------------------------------------------------------------------
def detect_fibonacci_ote(candles: list, lookback: int = 60) -> dict:
    window = candles[-lookback:] if len(candles) > lookback else candles
    cur = candles[-1]["close"]
    if len(window) < 10:
        return {"in_ote": False, "bias": "none", "fib_levels": None}

    sh = max(c["high"] for c in window)
    sl = min(c["low"]  for c in window)
    shi = max(range(len(window)), key=lambda i: window[i]["high"])
    sli = min(range(len(window)), key=lambda i: window[i]["low"])
    rng = sh - sl
    if rng == 0:
        return {"in_ote": False, "bias": "none", "fib_levels": None}

    if sli < shi:   # low before high → bullish move, now retracing → buy OTE
        ote_hi  = sh - 0.618 * rng
        ote_lo  = sh - 0.786 * rng
        ote_ent = sh - 0.705 * rng
        in_ote  = ote_lo <= cur <= ote_hi
        bias    = "bullish"
        retrace = (sh - cur) / rng * 100
    else:           # high before low → bearish move, now retracing → sell OTE
        ote_lo  = sl + 0.618 * rng
        ote_hi  = sl + 0.786 * rng
        ote_ent = sl + 0.705 * rng
        in_ote  = ote_lo <= cur <= ote_hi
        bias    = "bearish"
        retrace = (cur - sl) / rng * 100

    fib_levels = {
        "0%":    _r(sl if bias=="bullish" else sh),
        "23.6%": _r(sh - 0.236*rng if bias=="bullish" else sl + 0.236*rng),
        "38.2%": _r(sh - 0.382*rng if bias=="bullish" else sl + 0.382*rng),
        "50%":   _r((sh+sl)/2),
        "61.8%": _r(ote_hi),
        "70.5%": _r(ote_ent),
        "78.6%": _r(ote_lo),
        "100%":  _r(sh if bias=="bullish" else sl),
    }
    return {"in_ote": in_ote, "bias": bias,
            "ote_zone_high": _r(ote_hi), "ote_zone_low": _r(ote_lo),
            "ote_entry": _r(ote_ent),
            "retracement_pct": round(retrace, 1),
            "fib_levels": fib_levels}


# ---------------------------------------------------------------------------
# 7. Volume Profile
# ---------------------------------------------------------------------------
def detect_volume_profile(candles: list, lookback: int = 60, bins: int = 20) -> dict:
    window = candles[-lookback:] if len(candles) > lookback else candles
    cur = candles[-1]["close"]
    if not window:
        return {"poc": None, "vah": None, "val": None, "bias": "none"}

    lo = min(c["low"]  for c in window)
    hi = max(c["high"] for c in window)
    if hi == lo:
        return {"poc": None, "vah": None, "val": None, "bias": "none"}

    bsize = (hi - lo) / bins
    vbins = [0.0] * bins
    for c in window:
        vol = c.get("volume", 1)
        rng = c["high"] - c["low"]
        if rng == 0: continue
        b0 = int((c["low"]  - lo) / bsize)
        b1 = int((c["high"] - lo) / bsize)
        for b in range(max(0, b0), min(bins, b1+1)):
            olo = lo + b * bsize; ohi = lo + (b+1) * bsize
            overlap = (min(c["high"], ohi) - max(c["low"], olo)) / rng
            vbins[b] += vol * max(0, overlap)

    poc_idx = vbins.index(max(vbins))
    poc = lo + (poc_idx + 0.5) * bsize

    total = sum(vbins)
    target = total * 0.70
    sorted_b = sorted(range(bins), key=lambda i: vbins[i], reverse=True)
    va = set()
    acc = 0
    for b in sorted_b:
        acc += vbins[b]; va.add(b)
        if acc >= target: break
    vah = lo + (max(va)+1) * bsize
    val = lo + min(va)      * bsize

    bias = "bullish" if cur > poc else ("bearish" if cur < poc else "neutral")
    return {"poc": _r(poc), "vah": _r(vah), "val": _r(val), "bias": bias,
            "above_vah": cur > vah, "below_val": cur < val,
            "dist_to_poc_pct": round((cur-poc)/poc*100, 2)}


# ---------------------------------------------------------------------------
# 8. Premium / Discount
# ---------------------------------------------------------------------------
def detect_premium_discount(candles: list, lookback: int = 60) -> dict:
    window = candles[-lookback:] if len(candles) > lookback else candles
    cur = candles[-1]["close"]
    hi = max(c["high"] for c in window)
    lo = min(c["low"]  for c in window)
    rng = hi - lo
    if rng == 0:
        return {"zone": "equilibrium", "position_pct": 50.0}

    pct = (cur - lo) / rng * 100
    if   pct <= 25: zone = "deep_discount"
    elif pct <= 50: zone = "discount"
    elif pct <= 75: zone = "premium"
    else:           zone = "deep_premium"

    return {"zone": zone, "position_pct": round(pct, 1),
            "equilibrium": _r((hi+lo)/2),
            "range_high": _r(hi), "range_low": _r(lo)}


# ---------------------------------------------------------------------------
# Confluence scoring
# ---------------------------------------------------------------------------
def _score(ms, ob, fvg, liq, sd, fib, vp, pd_) -> dict:
    long_score = short_score = 0
    fired = []          # which concepts fired (for the checklist display)
    reasons = []        # plain English reasons

    # ── Market Structure (max 25) ──────────────────────────────────────────
    trend = ms.get("trend","")
    struct = ms.get("structure","")

    if trend == "bullish":
        long_score += 10; fired.append("trend_bullish")
        reasons.append("Bullish market structure (HH + HL)")
    elif trend == "bearish":
        short_score += 10; fired.append("trend_bearish")
        reasons.append("Bearish market structure (LH + LL)")

    if struct == "CHoCH_bullish":
        long_score += 15; fired.append("CHoCH_bullish")
        reasons.append("CHoCH ↑ — bearish trend broken, reversal UP likely ⚡")
    elif struct == "CHoCH_bearish":
        short_score += 15; fired.append("CHoCH_bearish")
        reasons.append("CHoCH ↓ — bullish trend broken, reversal DOWN likely ⚡")
    elif struct == "BOS_bullish":
        long_score += 8; fired.append("BOS_bullish")
        reasons.append("BOS ↑ — bullish trend continuation")
    elif struct == "BOS_bearish":
        short_score += 8; fired.append("BOS_bearish")
        reasons.append("BOS ↓ — bearish trend continuation")

    # ── Order Blocks (max 20) ─────────────────────────────────────────────
    if ob.get("in_bullish_ob"):
        long_score += 20; fired.append("OB_bullish_active")
        reasons.append(f"Price INSIDE bullish OB at {_r(ob['bullish_ob']['low'])}–{_r(ob['bullish_ob']['high'])} ✦")
    elif ob.get("bullish_ob"):
        long_score += 8; fired.append("OB_bullish_nearby")
        reasons.append(f"Bullish OB nearby at {_r(ob['bullish_ob']['high'])}")

    if ob.get("in_bearish_ob"):
        short_score += 20; fired.append("OB_bearish_active")
        reasons.append(f"Price INSIDE bearish OB at {_r(ob['bearish_ob']['low'])}–{_r(ob['bearish_ob']['high'])} ✦")
    elif ob.get("bearish_ob"):
        short_score += 8; fired.append("OB_bearish_nearby")
        reasons.append(f"Bearish OB above at {_r(ob['bearish_ob']['low'])}")

    # ── Fair Value Gaps (max 18) ──────────────────────────────────────────
    if fvg.get("entering_bullish_fvg"):
        long_score += 18; fired.append("FVG_bullish_active")
        reasons.append(f"Price ENTERING bullish FVG {_r(fvg['bullish_fvg']['low'])}–{_r(fvg['bullish_fvg']['high'])} ✦")
    elif fvg.get("bullish_fvg"):
        long_score += 7; fired.append("FVG_bullish_nearby")
        reasons.append(f"Bullish FVG below at {_r(fvg['bullish_fvg']['high'])}")

    if fvg.get("entering_bearish_fvg"):
        short_score += 18; fired.append("FVG_bearish_active")
        reasons.append(f"Price ENTERING bearish FVG {_r(fvg['bearish_fvg']['low'])}–{_r(fvg['bearish_fvg']['high'])} ✦")
    elif fvg.get("bearish_fvg"):
        short_score += 7; fired.append("FVG_bearish_nearby")
        reasons.append(f"Bearish FVG above at {_r(fvg['bearish_fvg']['low'])}")

    # ── Liquidity Sweeps (max 18 — highest conviction) ────────────────────
    if liq.get("swept_sell_side"):
        long_score += 18; fired.append("LIQ_sweep_ssl")
        reasons.append("SSL SWEPT ↑ — stop hunt complete, long reversal expected ⚡⚡")
    if liq.get("swept_buy_side"):
        short_score += 18; fired.append("LIQ_sweep_bsl")
        reasons.append("BSL SWEPT ↓ — stop hunt complete, short reversal expected ⚡⚡")

    # ── Supply & Demand (max 10) ──────────────────────────────────────────
    if sd.get("in_demand"):
        dz = sd["demand_zone"]
        pts = 10 if dz["tests"] <= 1 else 5
        long_score += pts; fired.append("SD_demand_active")
        reasons.append(f"Price in demand zone {_r(dz['low'])}–{_r(dz['high'])} (touched {dz['tests']}×)")
    elif sd.get("demand_zone"):
        long_score += 4; fired.append("SD_demand_nearby")

    if sd.get("in_supply"):
        sz = sd["supply_zone"]
        pts = 10 if sz["tests"] <= 1 else 5
        short_score += pts; fired.append("SD_supply_active")
        reasons.append(f"Price in supply zone {_r(sz['low'])}–{_r(sz['high'])} (touched {sz['tests']}×)")
    elif sd.get("supply_zone"):
        short_score += 4; fired.append("SD_supply_nearby")

    # ── Fibonacci OTE (max 8) ─────────────────────────────────────────────
    if fib.get("in_ote"):
        if fib.get("bias") == "bullish":
            long_score += 8; fired.append("FIB_OTE_bullish")
            reasons.append(f"In Fibonacci OTE zone ({fib.get('retracement_pct')}% retrace) — precision long")
        elif fib.get("bias") == "bearish":
            short_score += 8; fired.append("FIB_OTE_bearish")
            reasons.append(f"In Fibonacci OTE zone ({fib.get('retracement_pct')}% retrace) — precision short")

    # ── Volume Profile (max 6) ────────────────────────────────────────────
    if vp.get("poc"):
        if vp["bias"] == "bullish":
            long_score += 3; fired.append("VP_above_poc")
        elif vp["bias"] == "bearish":
            short_score += 3; fired.append("VP_below_poc")
        if vp.get("above_vah"):
            long_score += 3; fired.append("VP_above_vah")
            reasons.append(f"Price above VAH {_r(vp['vah'])} — strong bullish breakout")
        elif vp.get("below_val"):
            short_score += 3; fired.append("VP_below_val")
            reasons.append(f"Price below VAL {_r(vp['val'])} — strong bearish breakdown")

    # ── Premium / Discount (max 5) ────────────────────────────────────────
    zone = pd_.get("zone","")
    pct  = pd_.get("position_pct", 50)
    if zone in ("discount", "deep_discount"):
        long_score += 5; fired.append(f"PD_{zone}")
        reasons.append(f"Price in {zone.replace('_',' ')} ({pct}% of range) — SMC favours longs")
    elif zone in ("premium", "deep_premium"):
        short_score += 5; fired.append(f"PD_{zone}")
        reasons.append(f"Price in {zone.replace('_',' ')} ({pct}% of range) — SMC favours shorts")

    # ── Final direction & confidence ──────────────────────────────────────
    if long_score >= short_score:
        direction  = "long" if long_score > 15 else "neutral"
        confidence = min(100, long_score)
    else:
        direction  = "short" if short_score > 15 else "neutral"
        confidence = min(100, short_score)

    if confidence >= 70:
        label = "HIGH — consider entry"
    elif confidence >= 50:
        label = "MEDIUM — wait for confirmation"
    else:
        label = "LOW — skip / watch only"
        direction = "neutral"

    # ── Concept checklist (all 8 concepts, fired/not) ────────────────────
    all_concepts = [
        "Market Structure", "CHoCH", "BOS",
        "Order Block", "Fair Value Gap", "Liquidity Sweep",
        "Supply & Demand", "Fibonacci OTE", "Volume Profile", "Premium/Discount"
    ]
    checklist = {}
    for c in all_concepts:
        key = c.replace(" ","_").replace("/","_").lower()
        fired_names_lower = " ".join(fired).lower()
        checklist[c] = any(k in fired_names_lower for k in [
            key, key.replace("_",""), c.split()[0].lower()
        ])

    return {"direction": direction, "confidence": confidence,
            "confidence_label": label, "long_score": long_score,
            "short_score": short_score, "reasons": reasons,
            "fired": fired, "checklist": checklist}


# ---------------------------------------------------------------------------
# Entry / SL / Target calculation
# ---------------------------------------------------------------------------
def _calc_levels(direction, cur, ms, ob, fvg, liq, sd) -> dict:
    entry = cur
    sl = tp1 = tp2 = None

    if direction == "long":
        sl_candidates = []
        if ob.get("bullish_ob"):
            sl_candidates.append(ob["bullish_ob"]["low"] * 0.998)
        if sd.get("demand_zone"):
            sl_candidates.append(sd["demand_zone"]["low"] * 0.998)
        if ms.get("last_swing_low"):
            sl_candidates.append(ms["last_swing_low"] * 0.997)
        sl = max(sl_candidates) if sl_candidates else cur * 0.985

        tp1_c = []
        if fvg.get("bearish_fvg"):    tp1_c.append(fvg["bearish_fvg"]["low"])
        if ob.get("bearish_ob"):      tp1_c.append(ob["bearish_ob"]["low"])
        if liq.get("buy_side_liquidity"): tp1_c.append(liq["buy_side_liquidity"])
        tp1 = min(tp1_c) if tp1_c else cur * 1.015

        tp2_c = []
        if sd.get("supply_zone"):     tp2_c.append(sd["supply_zone"]["low"])
        tp2 = min(tp2_c) if tp2_c else cur * 1.030

    elif direction == "short":
        sl_candidates = []
        if ob.get("bearish_ob"):
            sl_candidates.append(ob["bearish_ob"]["high"] * 1.002)
        if sd.get("supply_zone"):
            sl_candidates.append(sd["supply_zone"]["high"] * 1.002)
        if ms.get("last_swing_high"):
            sl_candidates.append(ms["last_swing_high"] * 1.003)
        sl = min(sl_candidates) if sl_candidates else cur * 1.015

        tp1_c = []
        if fvg.get("bullish_fvg"):    tp1_c.append(fvg["bullish_fvg"]["high"])
        if ob.get("bullish_ob"):      tp1_c.append(ob["bullish_ob"]["high"])
        if liq.get("sell_side_liquidity"): tp1_c.append(liq["sell_side_liquidity"])
        tp1 = max(tp1_c) if tp1_c else cur * 0.985

        tp2_c = []
        if sd.get("demand_zone"):     tp2_c.append(sd["demand_zone"]["high"])
        tp2 = max(tp2_c) if tp2_c else cur * 0.970

    rr = None
    if sl and tp1:
        risk   = abs(cur - sl)
        reward = abs(tp1 - cur)
        rr     = round(min(reward / risk, 10.0), 2) if risk > 0 else None

    return {"entry": _r(entry), "stop_loss": _r(sl),
            "target1": _r(tp1), "target2": _r(tp2), "rr_ratio": rr}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def run_smc_scan(symbol: str, candles: list) -> dict:
    """
    Run full SMC scan on one coin.

    Parameters
    ----------
    symbol  : e.g. "BTCUSDT"
    candles : list of OHLCV dicts from price_waterfall (15m recommended)
              Each: {"open_time", "open", "high", "low", "close", "volume"}

    Returns
    -------
    dict with keys:
      symbol, direction, confidence, confidence_label,
      reasons, fired, checklist, levels,
      session, components
    """
    if not candles or len(candles) < 30:
        return {
            "symbol": symbol, "direction": "neutral", "confidence": 0,
            "confidence_label": "Insufficient data (need 30+ candles)",
            "reasons": [], "fired": [], "checklist": {},
            "levels": {}, "session": None, "components": {},
        }

    cur = candles[-1]["close"]

    ms   = detect_market_structure(candles)
    ob   = detect_order_blocks(candles)
    fvg  = detect_fvg(candles)
    liq  = detect_liquidity(candles)
    sd   = detect_supply_demand(candles)
    fib  = detect_fibonacci_ote(candles)
    vp   = detect_volume_profile(candles)
    pd_  = detect_premium_discount(candles)

    sig  = _score(ms, ob, fvg, liq, sd, fib, vp, pd_)
    lvl  = _calc_levels(sig["direction"], cur, ms, ob, fvg, liq, sd)

    # Session context
    zone = current_kill_zone()
    session_note = kill_zone_bias(zone)

    return {
        "symbol":           symbol,
        "current_price":    _r(cur),
        "direction":        sig["direction"],
        "confidence":       sig["confidence"],
        "confidence_label": sig["confidence_label"],
        "long_score":       sig["long_score"],
        "short_score":      sig["short_score"],
        "reasons":          sig["reasons"],
        "fired":            sig["fired"],
        "checklist":        sig["checklist"],
        "levels":           lvl,
        "session": {
            "active_kill_zone": zone,
            "note":             session_note,
            "high_probability": zone in ("London", "New York"),
        },
        "components": {
            "market_structure": ms,
            "order_blocks":     ob,
            "fair_value_gaps":  fvg,
            "liquidity":        liq,
            "supply_demand":    sd,
            "fibonacci":        fib,
            "volume_profile":   vp,
            "premium_discount": pd_,
        },
    }


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def _r(val):
    if val is None or not math.isfinite(float(val)): return None
    if val == 0: return 0
    mag = math.floor(math.log10(abs(val)))
    return round(val, max(0, 6 - mag - 1))


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import random
    random.seed(7)

    def make_candles(start, n=100, vol=0.025, seed=1):
        random.seed(seed)
        out, price = [], start
        for i in range(n):
            mv = price * random.uniform(-vol, vol)
            if i == 40: mv = price * 0.035   # bullish impulse → creates OB + BOS
            if i == 70: mv = -price * 0.02   # pullback → creates FVG
            o = price; c = max(o+mv, start*0.001)
            h = max(o,c)*(1+random.uniform(0,vol*0.4))
            l = max(min(o,c)*(1-random.uniform(0,vol*0.4)), start*0.001)
            out.append({"open_time":i,"open":o,"high":h,"low":l,"close":c,
                        "volume":random.uniform(5e5,3e6)*(5 if i==40 else 1)})
            price = c
        return out

    print("SMC Engine v2 — Screener Edition — Self Test")
    print("="*60)
    for name, start, seed in [
        ("BTC",  67500, 1), ("ETH", 3550, 2), ("WIF", 2.17, 3),
        ("JUP",  0.42,  4), ("PEPE",0.0000095, 5),
    ]:
        c = make_candles(start, seed=seed)
        r = run_smc_scan(f"{name}USDT", c)
        kz = r["session"]["active_kill_zone"] or "off-session"
        fired_str = ", ".join(r["fired"][:3]) or "none"
        print(f"{name:6} | {r['direction']:7} | conf={r['confidence']:3}%"
              f" | RR={r['levels'].get('rr_ratio') or '—'}"
              f" | session={kz}")
        print(f"       fired: {fired_str}")
        if r["reasons"]:
            print(f"       → {r['reasons'][0]}")
    print("="*60)
    print("All tests passed")
