import logging
import time
from datetime import date

import pandas as pd
import requests
from auth import auth
from config import (
    MAX_CANDLES_PER_REQUEST,
    RESAMPLE_MINUTES,
    TOSS_BASE_URL,
    SPARKLINE_BARS,
    SOXX_STOCKS,
    SUMMARY_TICKERS,
    INDEX_TICKERS,
    REQUEST_THROTTLE_SEC,
)

logger = logging.getLogger(__name__)

# symbol -> (캐시된 날짜, 전일 종가). 전일 종가는 하루 안에 안 바뀌므로 날짜당 1회만 조회.
_prev_close_cache: dict[str, tuple[date, float]] = {}

# 캐시 저장소
_cache = {"quotes": [], "summary": [], "index": [], "exchange_rate": None}


def _request_candle_page(symbol: str, interval: str, before: str | None = None) -> dict:
    """토스 /api/v1/candles 1회 호출 (1분봉 최대 200개). 401이면 토큰 강제 갱신 후 1회 재시도."""
    url = f"{TOSS_BASE_URL}/api/v1/candles"
    params = {
        "symbol": symbol,
        "interval": interval,
        "count": MAX_CANDLES_PER_REQUEST
    }
    if before is not None:
        params["before"] = before

    headers = {"Authorization": f"Bearer {auth.get_token()}"}
    response = requests.get(url, params=params, headers=headers, timeout=10)

    if response.status_code == 401:
        logger.warning(f"{symbol} 캔들 조회 401, 토큰 강제 갱신 후 재시도")
        headers = {"Authorization": f"Bearer {auth.force_refresh()}"}
        response = requests.get(url, params=params, headers=headers, timeout=10)

    response.raise_for_status()
    return response.json()["result"]


def _fetch_candles(symbol: str, min_count: int, interval: str) -> pd.DataFrame:
    """1분봉을 min_count개 이상 모일 때까지 `before` 페이지네이션으로 누적 조회.

    반환: timestamp 오름차순(과거 -> 최신) DataFrame, 컬럼 open/high/low/close/volume (float).
    """
    rows = []
    before = None

    while len(rows) < min_count:
        page = _request_candle_page(symbol, before=before, interval=interval)
        candles = page["candles"]
        if not candles:
            break
        rows.extend(candles)
        before = page.get("nextBefore")
        if before is None:
            break

    if not rows:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

    df = pd.DataFrame(rows)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.set_index("timestamp").sort_index()
    df = df.rename(
        columns={
            "openPrice": "open",
            "highPrice": "high",
            "lowPrice": "low",
            "closePrice": "close"
        }
    )
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def _resample(df_1m: pd.DataFrame, minutes: int) -> pd.DataFrame:
    """1분봉을 minutes 단위로 리샘플링 (spec §3.2 집계 규칙)."""
    rule = f"{minutes}min"
    resampled = df_1m.resample(rule).agg(
        {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
            "volume": "sum"
        }
    )
    return resampled.dropna(subset=["open", "high", "low", "close"])


def get_candles(symbol: str, interval: str, count: int) -> pd.DataFrame:
    """symbol의 캔들을 interval 단위로 최근 count개 반환.

    interval: '1m' | '5m' | '30m'.
    토스 API는 1m/1d만 지원하므로(spec §3.1), 5m/30m은 1m을 받아 리샘플링한다(spec §3.2).

    주의: 마지막 행이 아직 마감되지 않은(진행 중인) 봉일 수 있다.
    Entry 레이어처럼 마감된 봉만 써야 하는 호출부는 이 함수가 반환한 DataFrame의
    마지막 행을 직접 제외하고 사용해야 한다 (이 함수는 그 판단을 하지 않는다).
    """
    if interval == "1m":
        return _fetch_candles(symbol, count, interval).tail(count)
    elif interval == "1d":
        return _fetch_candles(symbol, count, interval).tail(count)

    if interval not in RESAMPLE_MINUTES:
        raise ValueError(f"지원하지 않는 interval: {interval}")

    minutes = RESAMPLE_MINUTES[interval]
    # count개의 리샘플 봉을 만들려면 1분봉이 최소 count*minutes개 필요.
    # 가장 오래된 구간은 봉 경계에 안 맞아 잘릴 수 있어 1구간만큼 여유를 더 받는다.
    raw_count = count * minutes + minutes
    df = _fetch_candles(symbol, raw_count, interval)
    return _resample(df, minutes).tail(count)


def _get_prev_close(symbol: str) -> float:
    """symbol의 전일 종가. 하루에 한 번만 실제 조회하고 그 뒤로는 캐시에서 반환."""
    today = date.today()
    cached = _prev_close_cache.get(symbol)
    if cached is not None and cached[0] == today:
        return cached[1]

    df_1d = get_candles(symbol, "1d", 2)
    prev_close = df_1d["close"].iloc[-2]
    _prev_close_cache[symbol] = (today, prev_close)
    return prev_close


def get_quote(symbol: str) -> dict:
    """symbol의 현재가/전일종가/등락률/스파크라인을 한 번에 반환."""
    df_1m = get_candles(symbol, "1m", SPARKLINE_BARS)   # 현재가 + 스파크라인
    prev_close = _get_prev_close(symbol)

    price = df_1m["close"].iloc[-1]
    change_rate = (price - prev_close) / prev_close * 100
    sparkline = df_1m["close"].tolist()

    return {
        "price": price,
        "prev_close": prev_close,
        "change_rate": change_rate,
        "sparkline": sparkline
        }


def get_all_quotes() -> list[dict]:
    """SOXX_STOCKS 전체 순회, 종목별 quote 조회. 실패한 종목은 건너뛰고 로그만 남김."""
    results = []
    errors = []

    for i, stock in enumerate(SOXX_STOCKS):
        if i > 0:
            time.sleep(REQUEST_THROTTLE_SEC)
        try:
            quote = get_quote(stock["ticker"])
            results.append({
                "ticker": stock["ticker"],
                "name": stock["name"],
                "weight": stock["weight"],
                **quote # price, prev_close, change_rate, sparkline
            })
        except Exception as e:
            logger.error(f"{stock["ticker"]} quote 조회 실패: {e}")
            errors.append(stock["ticker"])

    if errors:
        logger.warning(f"{len(errors)}개 종목 조회 실패: {', '.join(errors)}")

    return results


def _get_quotes_for(ticker_list: list[dict], label: str) -> list[dict]:
    """ticker_list([{ticker, name}, ...])를 순회하며 quote 조회. 실패한 종목은 건너뛰고 로그만 남김."""
    results = []

    for i, ticker_info in enumerate(ticker_list):
        if i > 0:
            time.sleep(REQUEST_THROTTLE_SEC)
        try:
            quote = get_quote(ticker_info["ticker"])
            results.append({
                "ticker": ticker_info["ticker"],
                "name": ticker_info["name"],
                **quote
            })
        except Exception as e:
            logger.error(f"{ticker_info['ticker']} {label} 조회 실패: {e}")

    return results


def get_summary() -> list[dict]:
    """대시보드 상단 요약 카드용. SUMMARY_TICKERS(SOXX/SOXL) 조회."""
    return _get_quotes_for(SUMMARY_TICKERS, "summary")


def get_index_summary() -> list[dict]:
    """지수 탭용. INDEX_TICKERS(SPY/QQQ) 조회."""
    return _get_quotes_for(INDEX_TICKERS, "index")


def get_exchange_rate() -> float:
    """USD/KRW 환율. 401이면 토큰 강제 갱신 후 1회 재시도"""
    url = f"{TOSS_BASE_URL}/api/v1/exchange-rate"
    params = {"baseCurrency": "USD", "quoteCurrency": "KRW"}

    headers = {"Authorization": f"Bearer {auth.get_token()}"}
    response = requests.get(url, params=params, headers=headers, timeout=10)

    if response.status_code == 401:
        logger.warning("환율 조회 401, 토큰 강제 갱신 후 재시도")
        headers = {"Authorization": f"Bearer {auth.force_refresh()}"}
        response = requests.get(url, params=params, headers=headers, timeout=10)

    response.raise_for_status()
    return float(response.json()["result"]["rate"])


def cache_updater():
    while True:
        try:
            _cache["summary"] = get_summary()
            _cache["index"] = get_index_summary()
            _cache["exchange_rate"] = get_exchange_rate()
        except Exception as e:
            logger.error(f"캐시 갱신 실패: {e}")

        time.sleep(5)  # 5초마다 갱신


def quote_cache_updater():
    while True:
        try:
            _cache["quotes"] = get_all_quotes()
        except Exception as e:
            logger.error(f"캐시 갱신 실패: {e}")
        
        time.sleep(15)  # 15초마다 갱신


# symbol -> 발행주식수. 거의 안 바뀌는 값이라 한 번 조회되면 계속 재사용.
_shares_outstanding_cache: dict[str, float] = {}


def _get_shares_outstanding(symbols: list[str]) -> dict[str, float]:
    """symbols의 발행주식수 조회. 이미 캐시된 심볼은 재조회하지 않음."""
    missing = [s for s in symbols if s not in _shares_outstanding_cache]
    if missing:
        url = f"{TOSS_BASE_URL}/api/v1/stocks"
        params = {"symbols": ",".join(missing)}

        headers = {"Authorization": f"Bearer {auth.get_token()}"}
        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code == 401:
            logger.warning(f"발행주식수 조회({params['symbols']}) 401, 토큰 강제 갱신 후 재시도")
            headers = {"Authorization": f"Bearer {auth.force_refresh()}"}
            response = requests.get(url, params=params, headers=headers, timeout=10)

        response.raise_for_status()
        for item in response.json()["result"]:
            _shares_outstanding_cache[item["symbol"]] = float(item["sharesOutstanding"])

    return {s: _shares_outstanding_cache[s] for s in symbols}


def get_market_cap_comparison() -> list[dict]:
    """SOXX/SOXL 시가총액 비교. 가격은 _cache["summary"]에서, 발행주식수는 별도 캐시에서 가져와 계산."""
    symbols = ["SOXX", "SOXL"]
    shares = _get_shares_outstanding(symbols)

    results = []
    for item in _cache["summary"]:
        if item["ticker"] not in symbols:
            continue
        results.append({
            "ticker": item["ticker"],
            "name": item["name"],
            "price": item["price"],
            "change_rate": item["change_rate"],
            "market_cap": item["price"] * shares[item["ticker"]],
        })
    return results
