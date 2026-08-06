import os
from dotenv import load_dotenv

load_dotenv()

TOSS_BASE_URL = "https://openapi.tossinvest.com"
TOSS_CLIENT_ID = os.environ["TOSS_CLIENT_ID"]
TOSS_CLIENT_SECRET = os.environ["TOSS_CLIENT_SECRET"]
TOKEN_REFRESH_BUFFER_SEC = 300

# 대시보드 상단 요약 카드용 (SOXX/SOXL 자체 시세)
SUMMARY_TICKERS = [
    {"ticker": "SOXX", "name": "iShares Semiconductor ETF"},
    {"ticker": "SOXL", "name": "Direxion Daily Semiconductor Bull 3X"},
]

# "지수" 탭용. 실제 지수 심볼 대신 추종 ETF로 대체 (Toss가 지수 자체는 캔들 조회 미지원).
INDEX_TICKERS = [
    {"ticker": "SPY", "name": "S&P 500"},
    {"ticker": "QQQ", "name": "Nasdaq 100"},
]

SOXX_STOCKS = [
    {"ticker": "NVDA", "name": "NVIDIA CORP", "weight": 8.87},
    {"ticker": "AMD", "name": "ADVANCED MICRO DEVICES INC", "weight": 8.51},
    {"ticker": "AVGO", "name": "BROADCOM INC", "weight": 7.96},
    {"ticker": "MU", "name": "MICRON TECHNOLOGY INC", "weight": 7.74},
    {"ticker": "AMAT", "name": "APPLIED MATERIAL INC", "weight": 5.22},
    {"ticker": "INTC", "name": "INTEL CORPORATION", "weight": 5.20},
    {"ticker": "TSM", "name": "TAIWAN SEMICONDUCTOR MANUFACTURING", "weight": 4.57},
    {"ticker": "KLAC", "name": "KLA CORP", "weight": 4.31},
    {"ticker": "MRVL", "name": "MARVELL TECHNOLOGY INC", "weight": 4.28},
    {"ticker": "LRCX", "name": "LAM RESEARCH CORP", "weight": 4.20},
    {"ticker": "TXN", "name": "TEXAS INSTRUMENT INC", "weight": 3.99},
    {"ticker": "ADI", "name": "ANALOG DEVICES INC", "weight": 3.96},
    {"ticker": "MPWR", "name": "MONOLITHIC POWER SYSTEMS INC", "weight": 3.59},
    {"ticker": "TER", "name": "TERADYNE INC", "weight": 3.21},
    {"ticker": "NXPI", "name": "NXP SEMICONDUCTORS NV", "weight": 3.16},
    {"ticker": "QCOM", "name": "QUALCOMM INC", "weight": 2.74},
    {"ticker": "ALAB", "name": "ASTERA LABS", "weight": 2.53},
    {"ticker": "ASML", "name": "ASML HOLDING ADR REPRESENTING", "weight": 2.40},
    {"ticker": "MCHP", "name": "MICROCHIP TECHNOLOGY INC", "weight": 2.25},
    {"ticker": "CRDO", "name": "CREDO TECHNOLOGY GROUP HOLDING LTD", "weight": 2.04},
]

SPARKLINE_BARS = 30

# ──────────────────────────────────────────
# 캔들 데이터 조회
# ──────────────────────────────────────────
# 토스 API는 1m, 1d 봉만 제공 → 5m/30m은 1m을 리샘플링해서 만든다
CANDLE_BASE_INTERVAL = "1m"
# 토스 /api/v1/candles 1회 호출당 최대 봉 개수
MAX_CANDLES_PER_REQUEST = 200
# 리샘플 대상 interval -> 몇 분 단위인지 매핑
RESAMPLE_MINUTES = {
    "5m": 5,
    "30m": 30,
}
# get_all_quotes()에서 종목별 요청 사이에 주는 딜레이(초).
# MARKET_DATA_CHART 그룹 초당 요청 한도(예시 스펙상 10건/초)를 안 넘기려는 용도.
REQUEST_THROTTLE_SEC = 0.3
