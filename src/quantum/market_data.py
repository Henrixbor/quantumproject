"""Default market data constants for quantum portfolio optimization."""

# Default market data (annualized) for common assets
DEFAULT_RETURNS: dict[str, float] = {
    "BTC": 0.65, "ETH": 0.80, "SOL": 1.20, "BNB": 0.40, "ADA": 0.35,
    "DOT": 0.30, "AVAX": 0.55, "MATIC": 0.45, "LINK": 0.40, "UNI": 0.35,
    "AAPL": 0.12, "GOOGL": 0.15, "MSFT": 0.14, "AMZN": 0.18, "TSLA": 0.35,
    "NVDA": 0.45, "META": 0.20, "SPY": 0.10, "QQQ": 0.13, "GLD": 0.05,
}

DEFAULT_VOLATILITY: dict[str, float] = {
    "BTC": 0.60, "ETH": 0.75, "SOL": 0.95, "BNB": 0.50, "ADA": 0.80,
    "DOT": 0.85, "AVAX": 0.90, "MATIC": 0.85, "LINK": 0.70, "UNI": 0.80,
    "AAPL": 0.22, "GOOGL": 0.25, "MSFT": 0.20, "AMZN": 0.28, "TSLA": 0.55,
    "NVDA": 0.45, "META": 0.35, "SPY": 0.15, "QQQ": 0.18, "GLD": 0.12,
}
