"""Application configuration. Public market data only; no credentials required."""
import os
from dotenv import load_dotenv

load_dotenv()

# CCXT spot-capable centralized venues. Availability is tested at runtime;
# configured does not mean reachable, licensed, or available to every user.
DEFAULT_EXCHANGE_IDS = (
    "binance", "bybit", "okx", "kucoin", "gate", "bitget", "mexc",
    "cryptocom", "coinbase", "kraken", "bitstamp", "gemini", "bitfinex",
    "bingx", "phemex", "poloniex", "bitvavo", "bitmart", "coinex",
    "lbank", "digifinex", "htx", "whitebit", "backpack", "hashkey",
    "bitrue", "bitso", "bitbank", "bitflyer", "bithumb",
)

EXCHANGE_IDS = tuple(
    item.strip().lower()
    for item in os.getenv("ARBIS_EXCHANGES", ",".join(DEFAULT_EXCHANGE_IDS)).split(",")
    if item.strip()
)

EXCHANGE_NAMES = {
    "binance": "Binance", "bybit": "Bybit", "okx": "OKX",
    "kucoin": "KuCoin", "gate": "Gate.io / Gate", "gateio": "Gate.io",
    "bitget": "Bitget", "mexc": "MEXC", "cryptocom": "Crypto.com",
    "coinbase": "Coinbase", "kraken": "Kraken", "bitstamp": "Bitstamp",
    "gemini": "Gemini", "bitfinex": "Bitfinex", "bingx": "BingX",
    "phemex": "Phemex", "poloniex": "Poloniex", "bitvavo": "Bitvavo",
    "bitmart": "BitMart", "coinex": "CoinEx", "lbank": "LBank",
    "digifinex": "DigiFinex", "htx": "HTX", "whitebit": "WhiteBIT",
    "backpack": "Backpack", "hashkey": "HashKey", "bitrue": "Bitrue",
    "bitso": "Bitso", "bitbank": "bitbank", "bitflyer": "bitFlyer",
    "bithumb": "Bithumb",
}

DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
SYMBOLS = tuple(
    symbol.strip()
    for symbol in os.getenv("ARBIS_SYMBOLS", ",".join(DEFAULT_SYMBOLS)).split(",")
    if symbol.strip()
)
REQUEST_TIMEOUT_MS = int(os.getenv("ARBIS_REQUEST_TIMEOUT_MS", "10000"))
MAX_DATA_AGE_SECONDS = int(os.getenv("ARBIS_MAX_DATA_AGE_SECONDS", "30"))
MAX_EXCHANGE_WORKERS = int(os.getenv("ARBIS_MAX_EXCHANGE_WORKERS", "6"))
