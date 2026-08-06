from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from data_loader import (
    _cache,
    cache_updater,
    quote_cache_updater,
    get_market_cap_comparison
    )
import threading

app = FastAPI()

@app.on_event("startup")
def startup_event():
    threading.Thread(target=cache_updater, daemon=True).start()
    threading.Thread(target=quote_cache_updater, daemon=True).start()


@app.get("/api/quotes")
def quotes():
    return _cache["quotes"]

@app.get("/api/summary")
def summary():
    return _cache["summary"]

@app.get("/api/index")
def index_summary():
    return _cache["index"]

@app.get("/api/exchange-rate")
def exchange_rate():
    return _cache["exchange_rate"]

@app.get("/api/market-cap")
def market_cap():
    return get_market_cap_comparison()

app.mount("/",
        StaticFiles(directory="static", html=True),
        name="static"
        )
