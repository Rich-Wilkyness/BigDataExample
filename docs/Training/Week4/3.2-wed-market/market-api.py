"""Supplied setup: a small replacement for the missing classroom market API."""
import random
from datetime import datetime, timezone
from itertools import count

from fastapi import FastAPI

app = FastAPI(title="Simulated market data")
sequence = count(1)
prices = {"AAPL": 226.37, "GOOG": 195.17, "MSFT": 431.28}


@app.get("/tick")
def tick():
    symbol = random.choice(list(prices))
    prices[symbol] = round(max(0.01, prices[symbol] + random.uniform(-0.10, 0.10)), 2)
    return {
        "sequence": next(sequence),
        "symbol": symbol,
        "price": prices[symbol],
        "size": random.choice([10, 50, 100, 200]),
        "side": random.choice(["BUY", "SELL"]),
        "exchange_ts": datetime.now(timezone.utc).isoformat(),
        "api_ts": datetime.now(timezone.utc).isoformat(),
    }
