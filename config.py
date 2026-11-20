"""Application configuration. No credentials are required for public market data."""
import os
from dotenv import load_dotenv

load_dotenv()

EXCHANGE_IDS = ("binance", "bybit", "okx")
DEFAULT_SYMBOLS = ("BTC/USDT", "ETH/USDT", "SOL/USDT")
SYMBOLS = tuple(
    symbol.strip()
    for symbol in os.getenv("ARBIS_SYMBOLS", ",".join(DEFAULT_SYMBOLS)).split(",")
    if symbol.strip()
)
REQUEST_TIMEOUT_MS = int(os.getenv("ARBIS_REQUEST_TIMEOUT_MS", "10000"))
MAX_DATA_AGE_SECONDS = 30
