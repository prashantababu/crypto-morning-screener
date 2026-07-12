"""
Coin universe for the Crypto Morning Screener.
Mirrors the structure of the F&O Morning Screener's symbol list,
organized by risk/liquidity category for scanning and heatmap grouping.
"""

COIN_UNIVERSE = {
    "tier1": [
        {"symbol": "BTCUSDT", "name": "Bitcoin", "options": True},
        {"symbol": "ETHUSDT", "name": "Ethereum", "options": True},
        {"symbol": "SOLUSDT", "name": "Solana", "options": True},
        {"symbol": "BNBUSDT", "name": "BNB", "options": True},
        {"symbol": "XRPUSDT", "name": "Ripple", "options": True},
        {"symbol": "ADAUSDT", "name": "Cardano", "options": False},
        {"symbol": "AVAXUSDT", "name": "Avalanche", "options": False},
        {"symbol": "DOGEUSDT", "name": "Dogecoin", "options": False},
        {"symbol": "LTCUSDT", "name": "Litecoin", "options": True},
        {"symbol": "LINKUSDT", "name": "Chainlink", "options": True},
    ],
    "midcap": [
        {"symbol": "MATICUSDT", "name": "Polygon", "options": False},
        {"symbol": "DOTUSDT", "name": "Polkadot", "options": False},
        {"symbol": "NEARUSDT", "name": "NEAR Protocol", "options": False},
        {"symbol": "ARBUSDT", "name": "Arbitrum", "options": False},
        {"symbol": "OPUSDT", "name": "Optimism", "options": False},
        {"symbol": "AAVEUSDT", "name": "Aave", "options": False},
        {"symbol": "UNIUSDT", "name": "Uniswap", "options": False},
        {"symbol": "ATOMUSDT", "name": "Cosmos", "options": False},
        {"symbol": "FTMUSDT", "name": "Fantom", "options": False},
        {"symbol": "INJUSDT", "name": "Injective", "options": False},
        {"symbol": "SUIUSDT", "name": "Sui", "options": False},
        {"symbol": "APTUSDT", "name": "Aptos", "options": False},
        {"symbol": "SEIUSDT", "name": "Sei", "options": False},
    ],
    "highrisk": [
        {"symbol": "WIFUSDT", "name": "dogwifhat", "options": False},
        {"symbol": "BONKUSDT", "name": "Bonk", "options": False},
        {"symbol": "PEPEUSDT", "name": "Pepe", "options": False},
        {"symbol": "FLOKIUSDT", "name": "Floki", "options": False},
        {"symbol": "SHIBUSDT", "name": "Shiba Inu", "options": False},
        {"symbol": "NOTUSDT", "name": "Notcoin", "options": False},
        {"symbol": "MEMEUSDT", "name": "Memecoin", "options": False},
    ],
    "defi": [
        {"symbol": "APEUSDT", "name": "ApeCoin", "options": False},
        {"symbol": "CRVUSDT", "name": "Curve", "options": False},
        {"symbol": "MKRUSDT", "name": "Maker", "options": False},
        {"symbol": "SUSHIUSDT", "name": "SushiSwap", "options": False},
        {"symbol": "COMPUSDT", "name": "Compound", "options": False},
        {"symbol": "GMXUSDT", "name": "GMX", "options": False},
    ],
    "narrative": [
        {"symbol": "RENDERUSDT", "name": "Render", "options": False},
        {"symbol": "FETUSDT", "name": "Fetch.ai", "options": False},
        {"symbol": "TIAUSDT", "name": "Celestia", "options": False},
        {"symbol": "JUPUSDT", "name": "Jupiter", "options": False},
        {"symbol": "PYTHUSDT", "name": "Pyth Network", "options": False},
        {"symbol": "STRKUSDT", "name": "Starknet", "options": False},
        {"symbol": "ALTUSDT", "name": "AltLayer", "options": False},
        {"symbol": "DYMUSDT", "name": "Dymension", "options": False},
    ],
}


def all_symbols():
    """Flat list of every symbol across categories."""
    out = []
    for coins in COIN_UNIVERSE.values():
        out.extend(c["symbol"] for c in coins)
    return out


def symbol_category(symbol):
    for cat, coins in COIN_UNIVERSE.items():
        if any(c["symbol"] == symbol for c in coins):
            return cat
    return "unknown"


def symbol_meta(symbol):
    for coins in COIN_UNIVERSE.values():
        for c in coins:
            if c["symbol"] == symbol:
                return c
    return {"symbol": symbol, "name": symbol, "options": False}
