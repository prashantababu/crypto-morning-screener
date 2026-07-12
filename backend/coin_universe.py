"""
Expanded 95-coin universe — Delta Exchange India Perpetuals + TradingView Watchlist
All symbols confirmed listed on Delta Exchange India as of July 2026.

Key notes for YOUR trading style (intraday, few hours, target 1-2% / $10-20):
  - Focus on Degen2 + HighRisk + Volatile categories for biggest intraday moves
  - xStock tokens move most during US market hours (7:30 PM - 2 AM IST)
  - Tier1 has best liquidity but smaller % moves -- better for larger size
  - max_lev shows Delta's max -- you should use 2-5x max at your capital size
  - Delta <> TradingView integration is live (June 2026): you can trade
    directly from TradingView charts using your Delta account
"""

COIN_UNIVERSE = {

    "Tier1": [
        {"symbol":"BTCUSDT",  "name":"Bitcoin",       "delta_symbol":"BTCUSD",  "max_lev":100, "options":True,  "tv":"BINANCE:BTCUSDT"},
        {"symbol":"ETHUSDT",  "name":"Ethereum",      "delta_symbol":"ETHUSD",  "max_lev":100, "options":True,  "tv":"BINANCE:ETHUSDT"},
        {"symbol":"SOLUSDT",  "name":"Solana",        "delta_symbol":"SOLUSD",  "max_lev":100, "options":False, "tv":"BINANCE:SOLUSDT"},
        {"symbol":"BNBUSDT",  "name":"BNB",           "delta_symbol":"BNBUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:BNBUSDT"},
        {"symbol":"XRPUSDT",  "name":"Ripple",        "delta_symbol":"XRPUSD",  "max_lev":100, "options":False, "tv":"BINANCE:XRPUSDT"},
        {"symbol":"ADAUSDT",  "name":"Cardano",       "delta_symbol":"ADAUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:ADAUSDT"},
        {"symbol":"AVAXUSDT", "name":"Avalanche",     "delta_symbol":"AVAXUSD", "max_lev":100, "options":False, "tv":"BINANCE:AVAXUSDT"},
        {"symbol":"DOGEUSDT", "name":"Dogecoin",      "delta_symbol":"DOGEUSD", "max_lev":100, "options":False, "tv":"BINANCE:DOGEUSDT"},
        {"symbol":"LTCUSDT",  "name":"Litecoin",      "delta_symbol":"LTCUSD",  "max_lev":100, "options":True,  "tv":"BINANCE:LTCUSDT"},
        {"symbol":"LINKUSDT", "name":"Chainlink",     "delta_symbol":"LINKUSD", "max_lev":100, "options":True,  "tv":"BINANCE:LINKUSDT"},
    ],

    "Midcap": [
        {"symbol":"MATICUSDT","name":"Polygon",       "delta_symbol":"MATICUSD","max_lev":50,  "options":False, "tv":"BINANCE:MATICUSDT"},
        {"symbol":"DOTUSDT",  "name":"Polkadot",      "delta_symbol":"DOTUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:DOTUSDT"},
        {"symbol":"NEARUSDT", "name":"NEAR Protocol", "delta_symbol":"NEARUSD", "max_lev":50,  "options":False, "tv":"BINANCE:NEARUSDT"},
        {"symbol":"ARBUSDT",  "name":"Arbitrum",      "delta_symbol":"ARBUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:ARBUSDT"},
        {"symbol":"OPUSDT",   "name":"Optimism",      "delta_symbol":"OPUSD",   "max_lev":50,  "options":False, "tv":"BINANCE:OPUSDT"},
        {"symbol":"AAVEUSDT", "name":"Aave",          "delta_symbol":"AAVEUSD", "max_lev":20,  "options":False, "tv":"BINANCE:AAVEUSDT"},
        {"symbol":"UNIUSDT",  "name":"Uniswap",       "delta_symbol":"UNIUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:UNIUSDT"},
        {"symbol":"ATOMUSDT", "name":"Cosmos",        "delta_symbol":"ATOMUSD", "max_lev":50,  "options":False, "tv":"BINANCE:ATOMUSDT"},
        {"symbol":"INJUSDT",  "name":"Injective",     "delta_symbol":"INJUSD",  "max_lev":20,  "options":False, "tv":"BINANCE:INJUSDT"},
        {"symbol":"SUIUSDT",  "name":"Sui",           "delta_symbol":"SUIUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:SUIUSDT"},
        {"symbol":"APTUSDT",  "name":"Aptos",         "delta_symbol":"APTUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:APTUSDT"},
        {"symbol":"SEIUSDT",  "name":"Sei",           "delta_symbol":"SEIUSD",  "max_lev":20,  "options":False, "tv":"BINANCE:SEIUSDT"},
        {"symbol":"FTMUSDT",  "name":"Fantom/Sonic",  "delta_symbol":"FTMUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:FTMUSDT"},
        {"symbol":"HYPEUSDT", "name":"Hyperliquid",   "delta_symbol":"HYPEUSD", "max_lev":20,  "options":False, "tv":"BINANCE:HYPEUSDT"},
        {"symbol":"STXUSDT",  "name":"Stacks",        "delta_symbol":"STXUSD",  "max_lev":20,  "options":False, "tv":"BINANCE:STXUSDT"},
        {"symbol":"MOVEUSDT", "name":"Movement",      "delta_symbol":"MOVEUSD", "max_lev":20,  "options":False, "tv":"BINANCE:MOVEUSDT"},
        {"symbol":"MANTAUSDT","name":"Manta Network", "delta_symbol":"MANTAUSD","max_lev":20,  "options":False, "tv":"BINANCE:MANTAUSDT"},
        {"symbol":"TRXUSDT",  "name":"Tron",          "delta_symbol":"TRXUSD",  "max_lev":50,  "options":False, "tv":"BINANCE:TRXUSDT"},
        {"symbol":"LDOUSDT",  "name":"Lido DAO",      "delta_symbol":"LDOUSD",  "max_lev":20,  "options":False, "tv":"BINANCE:LDOUSDT"},
        {"symbol":"IMXUSDT",  "name":"Immutable X",   "delta_symbol":"IMXUSD",  "max_lev":20,  "options":False, "tv":"BINANCE:IMXUSDT"},
        {"symbol":"DYDXUSDT", "name":"dYdX",          "delta_symbol":"DYDXUSD", "max_lev":20,  "options":False, "tv":"BINANCE:DYDXUSDT"},
    ],

    "HighRisk": [
        {"symbol":"WIFUSDT",  "name":"dogwifhat",     "delta_symbol":"WIFUSD",     "max_lev":20, "options":False, "tv":"BINANCE:WIFUSDT"},
        {"symbol":"BONKUSDT", "name":"Bonk",          "delta_symbol":"BONKUSD",    "max_lev":20, "options":False, "tv":"BINANCE:BONKUSDT"},
        {"symbol":"PEPEUSDT", "name":"Pepe",          "delta_symbol":"PEPEUSD",    "max_lev":50, "options":False, "tv":"BINANCE:PEPEUSDT"},
        {"symbol":"FLOKIUSDT","name":"Floki",         "delta_symbol":"FLOKIUSD",   "max_lev":20, "options":False, "tv":"BINANCE:FLOKIUSDT"},
        {"symbol":"SHIBUSDT", "name":"Shiba Inu",     "delta_symbol":"SHIBUSD",    "max_lev":50, "options":False, "tv":"BINANCE:SHIBUSDT"},
        {"symbol":"NOTUSDT",  "name":"Notcoin",       "delta_symbol":"NOTUSD",     "max_lev":20, "options":False, "tv":"BINANCE:NOTUSDT"},
        {"symbol":"MEMEUSDT", "name":"Memecoin",      "delta_symbol":"MEMEUSD",    "max_lev":20, "options":False, "tv":"BINANCE:MEMEUSDT"},
    ],

    "Degen2": [
        # Extreme movers -- intraday only, very wide spreads, use small size
        {"symbol":"FARTCOINUSDT","name":"Fartcoin",       "delta_symbol":"FARTCOINUSD","max_lev":20, "options":False, "tv":"BINANCE:FARTCOINUSDT"},
        {"symbol":"PENGUUSDT",   "name":"Pudgy Penguins", "delta_symbol":"PENGUUSD",   "max_lev":20, "options":False, "tv":"BINANCE:PENGUUSDT"},
        {"symbol":"TRUMPUSDT",   "name":"Official Trump", "delta_symbol":"TRUMPUSD",   "max_lev":20, "options":False, "tv":"BINANCE:TRUMPUSDT"},
        {"symbol":"SPXUSDT",     "name":"SPX6900",        "delta_symbol":"SPXUSD",     "max_lev":20, "options":False, "tv":"BINANCE:SPXUSDT"},
        {"symbol":"LISTAUSDT",   "name":"Lista DAO",      "delta_symbol":"LISTAUSD",   "max_lev":20, "options":False, "tv":"BINANCE:LISTAUSDT"},
        {"symbol":"XAIUSDT",     "name":"Xai",            "delta_symbol":"XAIUSD",     "max_lev":20, "options":False, "tv":"BINANCE:XAIUSDT"},
        {"symbol":"USUALUSDT",   "name":"Usual",          "delta_symbol":"USUALUSD",   "max_lev":20, "options":False, "tv":"BINANCE:USUALUSDT"},
        {"symbol":"CROSSUSDT",   "name":"Cross",          "delta_symbol":"CROSSUSD",   "max_lev":20, "options":False, "tv":"BINANCE:CROSSUSDT"},
        {"symbol":"BLURUSDT",    "name":"Blur",           "delta_symbol":"BLURUSD",    "max_lev":20, "options":False, "tv":"BINANCE:BLURUSDT"},
        {"symbol":"ACEUSDT",     "name":"Fusionist",      "delta_symbol":"ACEUSD",     "max_lev":20, "options":False, "tv":"BINANCE:ACEUSDT"},
    ],

    "DeFi": [
        {"symbol":"APEUSDT",   "name":"ApeCoin",      "delta_symbol":"APEUSD",   "max_lev":20, "options":False, "tv":"BINANCE:APEUSDT"},
        {"symbol":"CRVUSDT",   "name":"Curve",        "delta_symbol":"CRVUSD",   "max_lev":20, "options":False, "tv":"BINANCE:CRVUSDT"},
        {"symbol":"MKRUSDT",   "name":"Maker",        "delta_symbol":"MKRUSD",   "max_lev":20, "options":False, "tv":"BINANCE:MKRUSDT"},
        {"symbol":"SUSHIUSDT", "name":"SushiSwap",    "delta_symbol":"SUSHIUSD", "max_lev":20, "options":False, "tv":"BINANCE:SUSHIUSDT"},
        {"symbol":"COMPUSDT",  "name":"Compound",     "delta_symbol":"COMPUSD",  "max_lev":20, "options":False, "tv":"BINANCE:COMPUSDT"},
        {"symbol":"GMXUSDT",   "name":"GMX",          "delta_symbol":"GMXUSD",   "max_lev":20, "options":False, "tv":"BINANCE:GMXUSDT"},
        {"symbol":"ENAUSDT",   "name":"Ethena",       "delta_symbol":"ENAUSD",   "max_lev":20, "options":False, "tv":"BINANCE:ENAUSDT"},
        {"symbol":"EIGENUSDT", "name":"EigenLayer",   "delta_symbol":"EIGENUSD", "max_lev":20, "options":False, "tv":"BINANCE:EIGENUSDT"},
        {"symbol":"JUPUSDT",   "name":"Jupiter",      "delta_symbol":"JUPUSD",   "max_lev":20, "options":False, "tv":"BINANCE:JUPUSDT"},
    ],

    "Narrative": [
        {"symbol":"RENDERUSDT","name":"Render",             "delta_symbol":"RENDERUSD","max_lev":20, "options":False, "tv":"BINANCE:RENDERUSDT"},
        {"symbol":"FETUSDT",  "name":"Fetch.ai",            "delta_symbol":"FETUSD",  "max_lev":20, "options":False, "tv":"BINANCE:FETUSDT"},
        {"symbol":"TIAUSDT",  "name":"Celestia",            "delta_symbol":"TIAUSD",  "max_lev":20, "options":False, "tv":"BINANCE:TIAUSDT"},
        {"symbol":"PYTHUSDT", "name":"Pyth Network",        "delta_symbol":"PYTHUSD", "max_lev":20, "options":False, "tv":"BINANCE:PYTHUSDT"},
        {"symbol":"STRKUSDT", "name":"Starknet",            "delta_symbol":"STRKUSD", "max_lev":20, "options":False, "tv":"BINANCE:STRKUSDT"},
        {"symbol":"ALTUSDT",  "name":"AltLayer",            "delta_symbol":"ALTUSD",  "max_lev":20, "options":False, "tv":"BINANCE:ALTUSDT"},
        {"symbol":"DYMUSDT",  "name":"Dymension",           "delta_symbol":"DYMUSD",  "max_lev":20, "options":False, "tv":"BINANCE:DYMUSDT"},
        {"symbol":"TAOUSDT",  "name":"Bittensor",           "delta_symbol":"TAOUSD",  "max_lev":20, "options":False, "tv":"BINANCE:TAOUSDT"},
        {"symbol":"IOLUSDT",  "name":"io.net",              "delta_symbol":"IOLUSD",  "max_lev":20, "options":False, "tv":"BINANCE:IOLUSDT"},
        {"symbol":"ZETAUSDT", "name":"ZetaChain",           "delta_symbol":"ZETAUSD", "max_lev":20, "options":False, "tv":"BINANCE:ZETAUSDT"},
        {"symbol":"WLDUSDT",  "name":"Worldcoin",           "delta_symbol":"WLDUSD",  "max_lev":20, "options":False, "tv":"BINANCE:WLDUSDT"},
        {"symbol":"MEWUSDT",  "name":"cat in a dogs world", "delta_symbol":"MEWUSD",  "max_lev":20, "options":False, "tv":"BINANCE:MEWUSDT"},
        {"symbol":"TURBOUSDT","name":"Turbo",               "delta_symbol":"TURBOUSD","max_lev":20, "options":False, "tv":"BINANCE:TURBOUSDT"},
        {"symbol":"PNUTUSDT", "name":"Peanut the Squirrel", "delta_symbol":"PNUTUSD", "max_lev":20, "options":False, "tv":"BINANCE:PNUTUSDT"},
        {"symbol":"ZROUSDT",  "name":"LayerZero",           "delta_symbol":"ZROUSD",  "max_lev":20, "options":False, "tv":"BINANCE:ZROUSDT"},
        {"symbol":"BEAMUSDT", "name":"Beam",                "delta_symbol":"BEAMXUSD","max_lev":20, "options":False, "tv":"BINANCE:BEAMUSDT"},
        {"symbol":"MAGICUSDT","name":"Magic",               "delta_symbol":"MAGICUSD","max_lev":20, "options":False, "tv":"BINANCE:MAGICUSDT"},
    ],

    "xStock": [
        # Tokenized stock perpetuals on Delta -- HUGE moves during US market hours (7:30PM-2AM IST)
        {"symbol":"TSLAXUSD", "name":"Tesla xStock",   "delta_symbol":"TSLAXUSD", "max_lev":25, "options":False, "tv":"NASDAQ:TSLA"},
        {"symbol":"QQQXUSD",  "name":"Nasdaq xStock",  "delta_symbol":"QQQXUSD",  "max_lev":25, "options":False, "tv":"NASDAQ:QQQ"},
        {"symbol":"SPYXUSD",  "name":"S&P500 xStock",  "delta_symbol":"SPYXUSD",  "max_lev":25, "options":False, "tv":"AMEX:SPY"},
        {"symbol":"NVDAXUSD", "name":"Nvidia xStock",  "delta_symbol":"NVDAXUSD", "max_lev":25, "options":False, "tv":"NASDAQ:NVDA"},
        {"symbol":"AAPLXUSD", "name":"Apple xStock",   "delta_symbol":"AAPLXUSD", "max_lev":25, "options":False, "tv":"NASDAQ:AAPL"},
    ],

    "Volatile": [
        # High-beta altcoins -- 5-15% daily range typical, good for your $10-20 profit target
        {"symbol":"SNXUSDT",     "name":"Synthetix",          "delta_symbol":"SNXUSD",    "max_lev":20, "options":False, "tv":"BINANCE:SNXUSDT"},
        {"symbol":"GALAUSDT",    "name":"Gala",               "delta_symbol":"GALAUSD",   "max_lev":20, "options":False, "tv":"BINANCE:GALAUSDT"},
        {"symbol":"SANDUSDT",    "name":"The Sandbox",        "delta_symbol":"SANDUSD",   "max_lev":50, "options":False, "tv":"BINANCE:SANDUSDT"},
        {"symbol":"MANAUSDT",    "name":"Decentraland",       "delta_symbol":"MANAUSD",   "max_lev":50, "options":False, "tv":"BINANCE:MANAUSDT"},
        {"symbol":"1000SATSUSDT","name":"1000SATS",           "delta_symbol":"1000SATSUSD","max_lev":20,"options":False, "tv":"BINANCE:1000SATSUSDT"},
        {"symbol":"ORDIUSDT",    "name":"ORDI",               "delta_symbol":"ORDIUSD",   "max_lev":20, "options":False, "tv":"BINANCE:ORDIUSDT"},
        {"symbol":"RUNEUSDT",    "name":"THORChain",          "delta_symbol":"RUNEUSD",   "max_lev":20, "options":False, "tv":"BINANCE:RUNEUSDT"},
        {"symbol":"ANKRUSDT",    "name":"Ankr",               "delta_symbol":"ANKRUSD",   "max_lev":20, "options":False, "tv":"BINANCE:ANKRUSDT"},
        {"symbol":"AGIXUSDT",    "name":"SingularityNET",     "delta_symbol":"AGIXUSD",   "max_lev":20, "options":False, "tv":"BINANCE:AGIXUSDT"},
        {"symbol":"ENSUSDT",     "name":"ENS",                "delta_symbol":"ENSUSD",    "max_lev":20, "options":False, "tv":"BINANCE:ENSUSDT"},
        {"symbol":"HIGHUSDT",    "name":"Highstreet",         "delta_symbol":"HIGHUSD",   "max_lev":20, "options":False, "tv":"BINANCE:HIGHUSDT"},
        {"symbol":"YGGUSDT",     "name":"Yield Guild Games",  "delta_symbol":"YGGUSD",    "max_lev":20, "options":False, "tv":"BINANCE:YGGUSDT"},
        {"symbol":"LEVERUSDT",   "name":"LeverFi",            "delta_symbol":"LEVERUSD",  "max_lev":20, "options":False, "tv":"BINANCE:LEVERUSDT"},
        {"symbol":"PIXELUSDT",    "name":"Pixels",             "delta_symbol":"PIXELUSD",  "max_lev":20, "options":False, "tv":"BINANCE:PIXELUSDT"},
        {"symbol":"DOGSUSDT",     "name":"DOGS",               "delta_symbol":"DOGSUSD",   "max_lev":20, "options":False, "tv":"BINANCE:DOGSUSDT"},
        {"symbol":"ILVUSDT",      "name":"Illuvium",           "delta_symbol":"ILVCUSD",   "max_lev":20, "options":False, "tv":"BINANCE:ILVUSDT"},
    ],
}


def all_coins():
    seen = set()
    out = []
    for coins in COIN_UNIVERSE.values():
        for c in coins:
            if c["symbol"] not in seen:
                seen.add(c["symbol"])
                out.append(c)
    return out


def all_symbols():
    return [c["symbol"] for c in all_coins()]


def tradingview_watchlist():
    return ",".join(c["tv"] for c in all_coins())


def by_category():
    return COIN_UNIVERSE


def symbol_meta(symbol):
    for coins in COIN_UNIVERSE.values():
        for c in coins:
            if c["symbol"] == symbol:
                return c
    return {"symbol": symbol, "name": symbol, "max_lev": 20, "options": False}


def symbol_category(symbol):
    for cat, coins in COIN_UNIVERSE.items():
        if any(c["symbol"] == symbol for c in coins):
            return cat
    return "Unknown"


if __name__ == "__main__":
    coins = all_coins()
    print(f"Total unique coins: {len(coins)}")
    total = 0
    for cat, coin_list in COIN_UNIVERSE.items():
        print(f"  {cat:12s}: {len(coin_list):2d} coins")
        total += len(coin_list)
    print(f"  (Raw total with any overlap: {total})")
    print(f"\nOptions available on Delta: {sum(1 for c in coins if c.get('options'))}")
    print(f"100x leverage available:    {sum(1 for c in coins if c.get('max_lev',0) >= 100)}")
    print(f"20x leverage only:          {sum(1 for c in coins if c.get('max_lev',0) == 20)}")
    print(f"\nxStock tokens (US market hours): {[c['name'] for c in COIN_UNIVERSE['xStock']]}")
