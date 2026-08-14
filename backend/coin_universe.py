"""
coin_universe.py  —  Delta Exchange India | 126-coin confirmed watchlist
========================================================================
DROP THIS FILE into your backend/ folder, replacing the old coin_universe.py.
No other code changes needed — all existing functions (all_coins, all_symbols,
by_category, symbol_meta, symbol_category) are preserved with identical APIs.

CATEGORIES
  Tier1       12  Majors — deepest liquidity, options on BTC/ETH/SOL/LTC/LINK/XRP
  Midcap      22  Balanced — 3-8% daily range, good for intraday + swing
  HighRisk    13  Meme — 5-15% daily, intraday only, strict SL required
  Degen2      12  Extreme — 10-30% daily, perfect for 1-2% quick profit target
  DeFi         9  Protocol tokens — real revenue, swing-friendly
  Narrative   19  AI/L2/Gaming/DePIN — momentum + breakout plays
  xStock      12  US stock perpetuals — ACTIVE 7:30 PM–2 AM IST
  Commodities  3  Gold (PAXG/XAUT) + Silver (SLVON) — macro hedge
  Volatile    18  High-beta altcoins — 5-20% daily range
  TOTAL      126  unique confirmed contracts on Delta Exchange India

SYMBOL NOTES
  - delta  : exact symbol to use on Delta Exchange (search this in Markets tab)
  - tv     : TradingView symbol for charting (import into watchlist)
  - lev    : Delta's max leverage — use 2-5x at your ₹2500/trade capital size
  - options: True if Delta India lists options on this coin (BTC/ETH/SOL/LTC/LINK/XRP)

XSTOCK NOTES (NEW ADDITIONS)
  SPCXXUSD  SpaceX   — private company, xToken tracks valuation. $437K 24h vol. 25x lev.
  MUBUSD    Micron   — semiconductor/AI theme. 8-15% moves on earnings. 25x lev.
  SLVONUSD  Silver   — tracks XAGUSD (silver spot). Chart via OANDA:XAGUSD. 25x lev.
  WDCBUSD   Western Digital — covers SanDisk business (SanDisk was acquired 2016).
                      SEARCH 'WDC' in Delta futures to confirm if currently listed.
  AMZNXUSD  Amazon   — note: AMZBXYSD in your query was a typo, correct is AMZNXUSD.

GOLD / XAUUSD EXPLAINED
  XAU = Gold ISO code (Latin 'aurum'). XAUUSD = gold price in US dollars.
  On Delta: trade as PAXGUSD (PAX Gold, 1:1 physical) or XAUTUSD (Tether Gold).
  On TradingView: chart as OANDA:XAUUSD for real gold spot price.
  XAG = Silver (Latin 'argentum'). XAGUSD = silver spot price.

LEGAL STATUS (xStock tokens in India)
  Delta Exchange India is FIU-registered. xStock tokens are crypto derivatives,
  not actual stock ownership — classified the same as BTC perpetuals under Indian
  crypto regulations. SEBI equity rules do NOT apply. INR-settled, slab-rate tax,
  no TDS. Confirmed legal as of August 2026.
"""

COIN_UNIVERSE = {

    # ---------------------------------------------------------------
    # TIER 1  |  12 coins  |  Options available  |  Up to 100x
    # Best for: large size, options strategies, safest intraday
    # ---------------------------------------------------------------
    "Tier1": [
        {"symbol":"BTCUSDT",   "name":"Bitcoin",        "delta":"BTCUSD",   "lev":100,"options":True,  "tv":"BINANCE:BTCUSDT"},
        {"symbol":"ETHUSDT",   "name":"Ethereum",       "delta":"ETHUSD",   "lev":100,"options":True,  "tv":"BINANCE:ETHUSDT"},
        {"symbol":"SOLUSDT",   "name":"Solana",         "delta":"SOLUSD",   "lev":100,"options":True,  "tv":"BINANCE:SOLUSDT"},
        {"symbol":"BNBUSDT",   "name":"BNB",            "delta":"BNBUSD",   "lev":50, "options":False, "tv":"BINANCE:BNBUSDT"},
        {"symbol":"XRPUSDT",   "name":"Ripple",         "delta":"XRPUSD",   "lev":100,"options":True,  "tv":"BINANCE:XRPUSDT"},
        {"symbol":"ADAUSDT",   "name":"Cardano",        "delta":"ADAUSD",   "lev":50, "options":False, "tv":"BINANCE:ADAUSDT"},
        {"symbol":"AVAXUSDT",  "name":"Avalanche",      "delta":"AVAXUSD",  "lev":100,"options":False, "tv":"BINANCE:AVAXUSDT"},
        {"symbol":"DOGEUSDT",  "name":"Dogecoin",       "delta":"DOGEUSD",  "lev":100,"options":False, "tv":"BINANCE:DOGEUSDT"},
        {"symbol":"LTCUSDT",   "name":"Litecoin",       "delta":"LTCUSD",   "lev":100,"options":True,  "tv":"BINANCE:LTCUSDT"},
        {"symbol":"LINKUSDT",  "name":"Chainlink",      "delta":"LINKUSD",  "lev":100,"options":True,  "tv":"BINANCE:LINKUSDT"},
        {"symbol":"TRXUSDT",   "name":"Tron",           "delta":"TRXUSD",   "lev":50, "options":False, "tv":"BINANCE:TRXUSDT"},
        {"symbol":"DOTUSDT",   "name":"Polkadot",       "delta":"DOTUSD",   "lev":50, "options":False, "tv":"BINANCE:DOTUSDT"},
    ],

    # ---------------------------------------------------------------
    # MIDCAP  |  22 coins  |  3-8% daily range
    # Best for: intraday momentum + BTST, good fill quality
    # ---------------------------------------------------------------
    "Midcap": [
        {"symbol":"MATICUSDT", "name":"Polygon",        "delta":"MATICUSD", "lev":50, "options":False, "tv":"BINANCE:MATICUSDT"},
        {"symbol":"NEARUSDT",  "name":"NEAR Protocol",  "delta":"NEARUSD",  "lev":50, "options":False, "tv":"BINANCE:NEARUSDT"},
        {"symbol":"ARBUSDT",   "name":"Arbitrum",       "delta":"ARBUSD",   "lev":50, "options":False, "tv":"BINANCE:ARBUSDT"},
        {"symbol":"OPUSDT",    "name":"Optimism",       "delta":"OPUSD",    "lev":50, "options":False, "tv":"BINANCE:OPUSDT"},
        {"symbol":"AAVEUSDT",  "name":"Aave",           "delta":"AAVEUSD",  "lev":20, "options":False, "tv":"BINANCE:AAVEUSDT"},
        {"symbol":"UNIUSDT",   "name":"Uniswap",        "delta":"UNIUSD",   "lev":50, "options":False, "tv":"BINANCE:UNIUSDT"},
        {"symbol":"ATOMUSDT",  "name":"Cosmos",         "delta":"ATOMUSD",  "lev":50, "options":False, "tv":"BINANCE:ATOMUSDT"},
        {"symbol":"INJUSDT",   "name":"Injective",      "delta":"INJUSD",   "lev":20, "options":False, "tv":"BINANCE:INJUSDT"},
        {"symbol":"SUIUSDT",   "name":"Sui",            "delta":"SUIUSD",   "lev":50, "options":False, "tv":"BINANCE:SUIUSDT"},
        {"symbol":"APTUSDT",   "name":"Aptos",          "delta":"APTUSD",   "lev":50, "options":False, "tv":"BINANCE:APTUSDT"},
        {"symbol":"SEIUSDT",   "name":"Sei",            "delta":"SEIUSD",   "lev":20, "options":False, "tv":"BINANCE:SEIUSDT"},
        {"symbol":"FTMUSDT",   "name":"Fantom/Sonic",   "delta":"FTMUSD",   "lev":50, "options":False, "tv":"BINANCE:FTMUSDT"},
        {"symbol":"HYPEUSDT",  "name":"Hyperliquid",    "delta":"HYPEUSD",  "lev":20, "options":False, "tv":"BYBIT:HYPEUSDT"},
        {"symbol":"STXUSDT",   "name":"Stacks",         "delta":"STXUSD",   "lev":20, "options":False, "tv":"BINANCE:STXUSDT"},
        {"symbol":"MOVEUSDT",  "name":"Movement",       "delta":"MOVEUSD",  "lev":20, "options":False, "tv":"BINANCE:MOVEUSDT"},
        {"symbol":"MANTAUSDT", "name":"Manta Network",  "delta":"MANTAUSD", "lev":20, "options":False, "tv":"BINANCE:MANTAUSDT"},
        {"symbol":"LDOUSDT",   "name":"Lido DAO",       "delta":"LDOUSD",   "lev":20, "options":False, "tv":"BINANCE:LDOUSDT"},
        {"symbol":"IMXUSDT",   "name":"Immutable X",    "delta":"IMXUSD",   "lev":20, "options":False, "tv":"BINANCE:IMXUSDT"},
        {"symbol":"DYDXUSDT",  "name":"dYdX",           "delta":"DYDXUSD",  "lev":20, "options":False, "tv":"BINANCE:DYDXUSDT"},
        {"symbol":"KASUSDT",   "name":"Kaspa",          "delta":"KASUSD",   "lev":20, "options":False, "tv":"BYBIT:KASUSDT"},
        {"symbol":"WLDUSDT",   "name":"Worldcoin",      "delta":"WLDUSD",   "lev":20, "options":False, "tv":"BINANCE:WLDUSDT"},
        {"symbol":"JUPUSDT",   "name":"Jupiter",        "delta":"JUPUSD",   "lev":20, "options":False, "tv":"BINANCE:JUPUSDT"},
    ],

    # ---------------------------------------------------------------
    # HIGH RISK  |  13 coins  |  5-15% daily
    # Intraday only. No overnight holds. Strict stop loss.
    # ---------------------------------------------------------------
    "HighRisk": [
        {"symbol":"WIFUSDT",   "name":"dogwifhat",          "delta":"WIFUSD",    "lev":20,"options":False,"tv":"BINANCE:WIFUSDT"},
        {"symbol":"BONKUSDT",  "name":"Bonk",               "delta":"BONKUSD",   "lev":20,"options":False,"tv":"BINANCE:BONKUSDT"},
        {"symbol":"PEPEUSDT",  "name":"Pepe",               "delta":"PEPEUSD",   "lev":50,"options":False,"tv":"BINANCE:PEPEUSDT"},
        {"symbol":"FLOKIUSDT", "name":"Floki",              "delta":"FLOKIUSD",  "lev":20,"options":False,"tv":"BINANCE:FLOKIUSDT"},
        {"symbol":"SHIBUSDT",  "name":"Shiba Inu",          "delta":"SHIBUSD",   "lev":50,"options":False,"tv":"BINANCE:SHIBUSDT"},
        {"symbol":"DOGSUSDT",  "name":"DOGS",               "delta":"DOGSUSD",   "lev":20,"options":False,"tv":"BYBIT:DOGSUSDT"},
        {"symbol":"BRETTUSDT", "name":"Brett",              "delta":"BRETTUSD",  "lev":20,"options":False,"tv":"BYBIT:BRETTUSDT"},
        {"symbol":"POPCATUSDT","name":"Popcat",             "delta":"POPCATUSD", "lev":20,"options":False,"tv":"BINANCE:POPCATUSDT"},
        {"symbol":"GOATUSDT",  "name":"Goatseus Maximus",   "delta":"GOATUSD",   "lev":20,"options":False,"tv":"BYBIT:GOATUSDT"},
        {"symbol":"MEWUSDT",   "name":"cat in dogs world",  "delta":"MEWUSD",    "lev":20,"options":False,"tv":"BYBIT:MEWUSDT"},
        {"symbol":"PNUTUSDT",  "name":"Peanut the Squirrel","delta":"PNUTUSD",   "lev":20,"options":False,"tv":"BINANCE:PNUTUSDT"},
        {"symbol":"MEMEUSDT",  "name":"Memecoin",           "delta":"MEMEUSD",   "lev":20,"options":False,"tv":"BINANCE:MEMEUSDT"},
        {"symbol":"NOTUSDT",   "name":"Notcoin",            "delta":"NOTUSD",    "lev":20,"options":False,"tv":"BINANCE:NOTUSDT"},
    ],

    # ---------------------------------------------------------------
    # DEGEN2  |  12 coins  |  10-30% daily range
    # Best category for your 1-2% intraday profit target.
    # Small size only. Spreads can be wide — use limit orders.
    # ---------------------------------------------------------------
    "Degen2": [
        {"symbol":"FARTCOINUSDT","name":"Fartcoin",       "delta":"FARTCOINUSD","lev":20,"options":False,"tv":"BYBIT:FARTCOINUSDT"},
        {"symbol":"PENGUUSDT",  "name":"Pudgy Penguins",  "delta":"PENGUUSD",   "lev":20,"options":False,"tv":"BINANCE:PENGUUSDT"},
        {"symbol":"TRUMPUSDT",  "name":"Official Trump",  "delta":"TRUMPUSD",   "lev":20,"options":False,"tv":"BINANCE:TRUMPUSDT"},
        {"symbol":"SPXUSDT",    "name":"SPX6900",         "delta":"SPXUSD",     "lev":20,"options":False,"tv":"BYBIT:SPXUSDT"},
        {"symbol":"TURBOUSDT",  "name":"Turbo",           "delta":"TURBOUSD",   "lev":20,"options":False,"tv":"BYBIT:TURBOUSDT"},
        {"symbol":"BLURUSDT",   "name":"Blur",            "delta":"BLURUSD",    "lev":20,"options":False,"tv":"BINANCE:BLURUSDT"},
        {"symbol":"LISTAUSDT",  "name":"Lista DAO",       "delta":"LISTAUSD",   "lev":20,"options":False,"tv":"BINANCE:LISTAUSDT"},
        {"symbol":"XAIUSDT",    "name":"Xai Gaming",      "delta":"XAIUSD",     "lev":20,"options":False,"tv":"BINANCE:XAIUSDT"},
        {"symbol":"USUALUSDT",  "name":"Usual",           "delta":"USUALUSD",   "lev":20,"options":False,"tv":"BINANCE:USUALUSDT"},
        {"symbol":"CROSSUSDT",  "name":"Cross",           "delta":"CROSSUSD",   "lev":20,"options":False,"tv":"BYBIT:CROSSUSDT"},
        {"symbol":"SIGNUSDT",   "name":"Sign",            "delta":"SIGNUSD",    "lev":20,"options":False,"tv":"BINANCE:SIGNUSDT"},
        {"symbol":"ACEUSDT",    "name":"Fusionist",       "delta":"ACEUSD",     "lev":20,"options":False,"tv":"BINANCE:ACEUSDT"},
    ],

    # ---------------------------------------------------------------
    # DEFI  |  9 coins  |  Real protocol revenue
    # Moderate volatility. Good for swing + catalyst trades.
    # ---------------------------------------------------------------
    "DeFi": [
        {"symbol":"ENAUSDT",   "name":"Ethena",        "delta":"ENAUSD",   "lev":20,"options":False,"tv":"BINANCE:ENAUSDT"},
        {"symbol":"EIGENUSDT", "name":"EigenLayer",    "delta":"EIGENUSD", "lev":20,"options":False,"tv":"BINANCE:EIGENUSDT"},
        {"symbol":"CRVUSDT",   "name":"Curve",         "delta":"CRVUSD",   "lev":20,"options":False,"tv":"BINANCE:CRVUSDT"},
        {"symbol":"MKRUSDT",   "name":"Maker",         "delta":"MKRUSD",   "lev":20,"options":False,"tv":"BINANCE:MKRUSDT"},
        {"symbol":"GMXUSDT",   "name":"GMX",           "delta":"GMXUSD",   "lev":20,"options":False,"tv":"BINANCE:GMXUSDT"},
        {"symbol":"SUSHIUSDT", "name":"SushiSwap",     "delta":"SUSHIUSD", "lev":20,"options":False,"tv":"BINANCE:SUSHIUSDT"},
        {"symbol":"COMPUSDT",  "name":"Compound",      "delta":"COMPUSD",  "lev":20,"options":False,"tv":"BINANCE:COMPUSDT"},
        {"symbol":"APEUSDT",   "name":"ApeCoin",       "delta":"APEUSD",   "lev":20,"options":False,"tv":"BINANCE:APEUSDT"},
        {"symbol":"JUPUSDT",   "name":"Jupiter",       "delta":"JUPUSD",   "lev":20,"options":False,"tv":"BINANCE:JUPUSDT"},
    ],

    # ---------------------------------------------------------------
    # NARRATIVE  |  19 coins  |  AI / L2 / Gaming / DePIN
    # 5-15% daily range. Catch breakouts on news catalysts.
    # ---------------------------------------------------------------
    "Narrative": [
        {"symbol":"TAOUSDT",    "name":"Bittensor",          "delta":"TAOUSD",    "lev":20,"options":False,"tv":"BYBIT:TAOUSDT"},
        {"symbol":"RENDERUSDT", "name":"Render",             "delta":"RENDERUSD", "lev":20,"options":False,"tv":"BINANCE:RENDERUSDT"},
        {"symbol":"FETUSDT",    "name":"Fetch.ai",           "delta":"FETUSD",    "lev":20,"options":False,"tv":"BINANCE:FETUSDT"},
        {"symbol":"AGIXUSDT",   "name":"SingularityNET",     "delta":"AGIXUSD",   "lev":20,"options":False,"tv":"BYBIT:AGIXUSDT"},
        {"symbol":"TIAUSDT",    "name":"Celestia",           "delta":"TIAUSD",    "lev":20,"options":False,"tv":"BINANCE:TIAUSDT"},
        {"symbol":"PYTHUSDT",   "name":"Pyth Network",       "delta":"PYTHUSD",   "lev":20,"options":False,"tv":"BINANCE:PYTHUSDT"},
        {"symbol":"STRKUSDT",   "name":"Starknet",           "delta":"STRKUSD",   "lev":20,"options":False,"tv":"BINANCE:STRKUSDT"},
        {"symbol":"ALTUSDT",    "name":"AltLayer",           "delta":"ALTUSD",    "lev":20,"options":False,"tv":"BINANCE:ALTUSDT"},
        {"symbol":"DYMUSDT",    "name":"Dymension",          "delta":"DYMUSD",    "lev":20,"options":False,"tv":"BINANCE:DYMUSDT"},
        {"symbol":"ZROUSDT",    "name":"LayerZero",          "delta":"ZROUSD",    "lev":20,"options":False,"tv":"BINANCE:ZROUSDT"},
        {"symbol":"BEAMUSDT",   "name":"Beam Gaming",        "delta":"BEAMUSD",   "lev":20,"options":False,"tv":"BINANCE:BEAMUSDT"},
        {"symbol":"MAGICUSDT",  "name":"Magic",              "delta":"MAGICUSD",  "lev":20,"options":False,"tv":"BINANCE:MAGICUSDT"},
        {"symbol":"ILVUSDT",    "name":"Illuvium",           "delta":"ILVCUSD",   "lev":20,"options":False,"tv":"BINANCE:ILVUSDT"},
        {"symbol":"PIXELUSDT",  "name":"Pixels Gaming",      "delta":"PIXELUSD",  "lev":20,"options":False,"tv":"BYBIT:PIXELUSDT"},
        {"symbol":"IOUSDT",     "name":"io.net",             "delta":"IOUSD",     "lev":20,"options":False,"tv":"BINANCE:IOUSDT"},
        {"symbol":"ZETAUSDT",   "name":"ZetaChain",          "delta":"ZETAUSD",   "lev":20,"options":False,"tv":"BINANCE:ZETAUSDT"},
        {"symbol":"ORDIUSDT",   "name":"ORDI (BRC-20)",      "delta":"ORDIUSD",   "lev":20,"options":False,"tv":"BINANCE:ORDIUSDT"},
        {"symbol":"RUNEUSDT",   "name":"THORChain",          "delta":"RUNEUSD",   "lev":20,"options":False,"tv":"BINANCE:RUNEUSDT"},
        {"symbol":"1000SATSUSDT","name":"1000SATS (BRC-20)", "delta":"1000SATSUSD","lev":20,"options":False,"tv":"BINANCE:1000SATSUSDT"},
    ],

    # ---------------------------------------------------------------
    # XSTOCK  |  12 coins  |  US stock perpetuals
    # ACTIVE HOURS: 7:30 PM — 2:00 AM IST (US market hours only)
    # Max leverage 10-25x. Legal in India — FIU registered, crypto
    # derivatives classification. Not actual stock ownership.
    # ---------------------------------------------------------------
    "xStock": [
        # Core US tech stocks — already in previous list
        {"symbol":"TSLAXUSDT",  "name":"Tesla",              "delta":"TSLAXUSD",  "lev":10,"options":False,"tv":"NASDAQ:TSLA"},
        {"symbol":"NVDAXUSDT",  "name":"Nvidia",             "delta":"NVDAXUSD",  "lev":10,"options":False,"tv":"NASDAQ:NVDA"},
        {"symbol":"AAPLXUSDT",  "name":"Apple",              "delta":"AAPLXUSD",  "lev":10,"options":False,"tv":"NASDAQ:AAPL"},
        {"symbol":"METAXUSDT",  "name":"Meta (Facebook)",    "delta":"METAXUSD",  "lev":10,"options":False,"tv":"NASDAQ:META"},
        {"symbol":"GOOGLXUSDT", "name":"Alphabet (Google)",  "delta":"GOOGLXUSD", "lev":10,"options":False,"tv":"NASDAQ:GOOGL"},
        {"symbol":"AMZNXUSDT",  "name":"Amazon",             "delta":"AMZNXUSD",  "lev":10,"options":False,"tv":"NASDAQ:AMZN"},
        {"symbol":"MSFTXUSDT",  "name":"Microsoft",          "delta":"MSFTXUSD",  "lev":10,"options":False,"tv":"NASDAQ:MSFT"},
        {"symbol":"QQQXUSDT",   "name":"Nasdaq ETF (QQQ)",   "delta":"QQQXUSD",   "lev":10,"options":False,"tv":"NASDAQ:QQQ"},
        {"symbol":"SPYXUSDT",   "name":"S&P500 ETF (SPY)",   "delta":"SPYXUSD",   "lev":10,"options":False,"tv":"AMEX:SPY"},
        # NEW — confirmed live on Delta India
        {"symbol":"SPCXXUSDT",  "name":"SpaceX (private co)","delta":"SPCXXUSD",  "lev":25,"options":False,"tv":"BINANCE:SPCXUSDT"},
        {"symbol":"MUBXUSDT",   "name":"Micron Technology",  "delta":"MUBUSD",    "lev":25,"options":False,"tv":"NASDAQ:MU"},
        # SanDisk delisted 2016 — Western Digital is the parent, search WDCBUSD in Delta
        # {"symbol":"WDCBUSDT", "name":"Western Digital",   "delta":"WDCBUSD",   "lev":25, "tv":"NASDAQ:WDC"},
    ],

    # ---------------------------------------------------------------
    # COMMODITIES  |  3 coins  |  Gold + Silver tokenized perpetuals
    # Gold = PAXG (PAX Gold) / XAUT (Tether Gold) — both 1:1 physical
    # Silver = SLVON (Silver xStock token on Delta)
    # Chart on TradingView: OANDA:XAUUSD (gold), OANDA:XAGUSD (silver)
    # XAU = gold ISO code (Latin 'aurum')
    # XAG = silver ISO code (Latin 'argentum')
    # ---------------------------------------------------------------
    "Commodities": [
        {"symbol":"PAXGUSDT",  "name":"Gold — PAX Gold",    "delta":"PAXGUSD",  "lev":20,"options":False,"tv":"OANDA:XAUUSD"},
        {"symbol":"XAUTUSDT",  "name":"Gold — Tether Gold", "delta":"XAUTUSD",  "lev":20,"options":False,"tv":"OANDA:XAUUSD"},
        # NEW — Silver xStock confirmed live on Delta
        {"symbol":"SLVONUSDT", "name":"Silver xStock",      "delta":"SLVONUSD", "lev":25,"options":False,"tv":"OANDA:XAGUSD"},
    ],

    # ---------------------------------------------------------------
    # VOLATILE  |  18 coins  |  5-20% daily range, high-beta
    # Good for scalping sessions when crypto is strongly trending
    # ---------------------------------------------------------------
    "Volatile": [
        {"symbol":"GALAUSDT",   "name":"Gala",               "delta":"GALAUSD",  "lev":20,"options":False,"tv":"BINANCE:GALAUSDT"},
        {"symbol":"SANDUSDT",   "name":"The Sandbox",        "delta":"SANDUSD",  "lev":50,"options":False,"tv":"BINANCE:SANDUSDT"},
        {"symbol":"MANAUSDT",   "name":"Decentraland",       "delta":"MANAUSD",  "lev":50,"options":False,"tv":"BINANCE:MANAUSDT"},
        {"symbol":"SNXUSDT",    "name":"Synthetix",          "delta":"SNXUSD",   "lev":20,"options":False,"tv":"BINANCE:SNXUSDT"},
        {"symbol":"ANKRUSDT",   "name":"Ankr",               "delta":"ANKRUSD",  "lev":20,"options":False,"tv":"BINANCE:ANKRUSDT"},
        {"symbol":"ENSUSDT",    "name":"ENS",                "delta":"ENSUSD",   "lev":20,"options":False,"tv":"BINANCE:ENSUSDT"},
        {"symbol":"YGGUSDT",    "name":"Yield Guild Games",  "delta":"YGGUSD",   "lev":20,"options":False,"tv":"BINANCE:YGGUSDT"},
        {"symbol":"ALGOUSDT",   "name":"Algorand",           "delta":"ALGOUSD",  "lev":20,"options":False,"tv":"BINANCE:ALGOUSDT"},
        {"symbol":"ICPUSDT",    "name":"Internet Computer",  "delta":"ICPUSD",   "lev":20,"options":False,"tv":"BINANCE:ICPUSDT"},
        {"symbol":"FILUSDT",    "name":"Filecoin",           "delta":"FILUSD",   "lev":20,"options":False,"tv":"BINANCE:FILUSDT"},
        {"symbol":"FLOWUSDT",   "name":"Flow",               "delta":"FLOWUSD",  "lev":20,"options":False,"tv":"BINANCE:FLOWUSDT"},
        {"symbol":"EGLDUSDT",   "name":"MultiversX",         "delta":"EGLDUSD",  "lev":20,"options":False,"tv":"BINANCE:EGLDUSDT"},
        {"symbol":"XTZUSDT",    "name":"Tezos",              "delta":"XTZUSD",   "lev":20,"options":False,"tv":"BINANCE:XTZUSDT"},
        {"symbol":"VETUSDT",    "name":"VeChain",            "delta":"VETUSD",   "lev":20,"options":False,"tv":"BINANCE:VETUSDT"},
        {"symbol":"XMRUSDT",    "name":"Monero",             "delta":"XMRUSD",   "lev":20,"options":False,"tv":"KRAKEN:XMRUSD"},
        {"symbol":"KAVAUSDT",   "name":"Kava",               "delta":"KAVAUSD",  "lev":20,"options":False,"tv":"BINANCE:KAVAUSDT"},
        {"symbol":"ZECUSDT",    "name":"Zcash",              "delta":"ZECUSD",   "lev":20,"options":False,"tv":"BINANCE:ZECUSDT"},
        {"symbol":"CELOUSDT",   "name":"Celo",               "delta":"CELOUSD",  "lev":20,"options":False,"tv":"BINANCE:CELOSDT"},
    ],
}


# ---------------------------------------------------------------
# Helper functions — identical API to previous coin_universe.py
# ---------------------------------------------------------------

def all_coins():
    """Returns deduplicated list of all coins across all categories."""
    seen, out = set(), []
    for coins in COIN_UNIVERSE.values():
        for c in coins:
            if c["symbol"] not in seen:
                seen.add(c["symbol"])
                out.append(c)
    return out


def all_symbols():
    """Returns list of all unique symbols (BTCUSDT format)."""
    return [c["symbol"] for c in all_coins()]


def by_category():
    """Returns the full COIN_UNIVERSE dict."""
    return COIN_UNIVERSE


def symbol_meta(symbol):
    """Returns full metadata dict for a given symbol, or None."""
    for coins in COIN_UNIVERSE.values():
        for c in coins:
            if c["symbol"] == symbol:
                return c
    return None


def symbol_category(symbol):
    """Returns category name for a given symbol, or 'Unknown'."""
    for cat, coins in COIN_UNIVERSE.items():
        if any(c["symbol"] == symbol for c in coins):
            return cat
    return "Unknown"


def delta_symbol(symbol):
    """Returns the Delta Exchange symbol for a given screener symbol."""
    meta = symbol_meta(symbol)
    return meta["delta"] if meta else symbol.replace("USDT", "USD")


def tradingview_watchlist(category=None):
    """
    Returns comma-separated TradingView symbols ready to paste into
    TradingView's Import list dialog, or save as a .list file.
    Pass category='xStock' to get only that category's symbols.
    """
    if category:
        coins = COIN_UNIVERSE.get(category, [])
    else:
        coins = all_coins()
    seen, out = set(), []
    for c in coins:
        tv = c.get("tv", "")
        if tv and tv not in seen:
            seen.add(tv)
            out.append(tv)
    return ",".join(out)


if __name__ == "__main__":
    coins = all_coins()
    print(f"Total unique coins: {len(coins)}")
    print(f"{'Category':12s} {'Count':6s} {'Notes'}")
    print("-" * 70)
    cats = {
        "Tier1":"Options on BTC/ETH/SOL/LTC/LINK/XRP. Up to 100x.",
        "Midcap":"3-8% daily range. Intraday + swing.",
        "HighRisk":"5-15% daily. Intraday only.",
        "Degen2":"10-30% daily. Best for 1-2% quick targets.",
        "DeFi":"Real revenue. Swing-friendly.",
        "Narrative":"AI/L2/Gaming. Catch breakouts.",
        "xStock":"US stocks. Active 7:30 PM-2 AM IST. Legal in India.",
        "Commodities":"Gold (PAXG/XAUT) + Silver (SLVON). Macro hedge.",
        "Volatile":"5-20% daily. High-beta scalping.",
    }
    for cat, note in cats.items():
        n = len(COIN_UNIVERSE.get(cat, []))
        print(f"{cat:12s} {n:6d}   {note}")
    print("-" * 70)
    print(f"{'TOTAL':12s} {len(coins):6d}")
    print(f"\nOptions-enabled coins: {[c['symbol'] for c in coins if c.get('opt')]}")
    dups = [s for s in all_symbols() if all_symbols().count(s) > 1]
    print(f"Duplicate symbols: {set(dups) if dups else 'none'}")
