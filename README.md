# SOXX Semiconductor Dashboard

SOXX(iShares Semiconductor ETF) 상위 20개 구성종목과 지수, 시가총액 비교까지 한눈에 보여주는 로컬 대시보드입니다.
미국 반도체 종목들의 현재가, 전일 대비 등락률, 최근 가격 흐름을 실시간으로 확인할 수 있습니다.

## Features

- ✅ SOXX 상위 20종목 비중 데이터 (iShares 공식 holdings 기준)
- ✅ Toss Open API 연동 — OAuth2 client credentials 인증, 자동 토큰 갱신
- ✅ 분봉/일봉 캔들 조회 (네이티브 1m/1d + 5m/30m 리샘플링)
- ✅ 전일 대비 등락률 계산 + 20종목 전체 시세 조회
- ✅ SOXX/SOXL 자체 시세 요약 카드, S&P500/나스닥(SPY/QQQ) 지수 탭
- ✅ SOXX vs SOXL 시가총액 비교 (발행주식수 × 현재가)
- ✅ USD/KRW 환율 표시 + 종목별 원화 환산가
- ✅ 탭 네비게이션 (대시보드 / 지수 / 시총비교)
- ✅ 숫자가 바뀔 때 옛값→새값으로 부드럽게 굴러가는 롤링 애니메이션 + 상승/하락 플래시 효과
- ✅ 서버 사이드 캐싱 — 백그라운드 스레드가 주기적으로 미리 갱신, API 응답은 항상 즉시(수십 ms) 반환
- ✅ 10초 내외 자동 갱신, SVG 스파크라인

## Tech Stack

- **Backend**: Python, FastAPI, pandas
- **Frontend**: HTML / CSS / vanilla JavaScript (no framework)
- **Data source**: [Toss Open API](https://openapi.tossinvest.com) (candle/price/exchange-rate/stock info)

## Why these choices

- 순수 JS로 프론트엔드를 구성해 프레임워크 없이 fetch 기반 폴링, SVG 렌더링, 숫자 애니메이션(`requestAnimationFrame`)을 직접 구현합니다.
- OAuth 토큰 발급/갱신은 서버 사이드에서만 처리해 클라이언트에 시크릿이 노출되지 않도록 설계했습니다.
- 종목별 캔들 조회는 API rate limit이 있어(20종목 × 반복 조회 시 초당 요청 한도 초과), 매 요청마다 즉시 조회하는 대신 서버가 백그라운드에서 주기적으로 미리 갱신해 캐시에 저장하고, API는 캐시를 즉시 반환하는 구조로 설계했습니다.
- 종목 비중은 iShares 공식 holdings CSV를 기준으로 하드코딩하며, 자동 연동은 이후 버전 과제로 남겨두었습니다.
- 실제 지수(S&P500/나스닥) 값 자체는 Toss가 제공하지 않아 추종 ETF(SPY/QQQ) 가격으로 대체했습니다.

## Setup

```bash
pip install -r requirements.txt
```

`.env` 파일에 Toss Open API 인증 정보를 설정합니다:

```
TOSS_CLIENT_ID=your_client_id
TOSS_CLIENT_SECRET=your_client_secret
```

```bash
uvicorn dashboard_server:app --reload
```

브라우저에서 `localhost:8000` 접속. (백그라운드 캐시가 채워지는 데 서버 기동 후 최대 15초 정도 걸릴 수 있습니다.)

## Project Structure

```
soxx_dashboard/
├── auth.py           # Toss OAuth2 토큰 관리
├── config.py          # 종목 목록, API 설정
├── dashboard_server.py  # FastAPI 서버 — 백그라운드 캐시 갱신 스레드 시작, 캐시 반환 라우트
├── data_loader.py      # 캔들/시세/환율/시총 조회 및 캐시 갱신 로직
└── static/index.html   # 대시보드 UI (탭, 카드, 표, 애니메이션)
```

## Not included (by design)

- 뉴스 피드 — 별도 외부 뉴스 API 연동이 필요해 이번 범위에서 제외했습니다.
- 배포/24시간 상시 구동 — 장중에만 로컬에서 켜서 보는 개인용 도구로 설계했습니다.

## License

Personal project, not for redistribution.
