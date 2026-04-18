# Changelog

All notable changes to **chart-analyzer** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- 대시보드 연동 (카드 + 결과 렌더링)
- Walk-forward parameter 최적화 CLI

---

## [0.2.1] — 2026-04-18

### Added
- **GitHub Actions Daily Pipeline** (`.github/workflows/daily_pipeline.yml`)
  - 매주 평일(Mon-Fri) KST 08:00 (UTC 23:00 prev) 자동 실행
  - 3개 sibling 레포(chart-analyzer + trendline-detector + backtest-lab) 동시 checkout
  - `workflow_dispatch`로 수동 실행 시 입력 파라미터 커스터마이즈 가능
    (tickers, days, chart_type, backtest_strategy, analysis_type)
  - 결과 artifact 14일 보존
  - 실패 시 자동 Telegram 알림
  - 필요 secrets: ANTHROPIC_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

### Changed
- `src/pipeline/__main__.py`: `--backtest` 선택지에 `bollinger_breakout`, `macd_divergence` 추가
  (backtest-lab v0.2.0과 연동)

---

## [0.2.0] — 2026-04-18

### Added
- **Cross-repo integration pipeline** (`src/pipeline/`)
  - `integrator.py`: sibling repo discovery + 동적 모듈 임포트
  - 4-전략 탐색 순서: env var → sibling dir → common paths → auto-clone
  - `CHART_ANALYZER_SIBLING_PATH` 환경변수로 strict 모드 지원
  - `sys.modules` unique namespace로 `src/` 충돌 방지
  - `~/.cache/chart-analyzer/siblings/`로 자동 git clone 폴백
- **High-level API**
  - `run_detection(ticker)`: trendline-detector 실행 → JSON 반환
  - `run_backtest(ticker, strategy)`: backtest-lab 실행 → summary + HTML
  - `run_full_pipeline(ticker)`: 전체 end-to-end (검출 → 차트 + 오버레이 → AI 분석 → 백테스트 → Telegram)
- **통합 CLI** (`python -m src.pipeline`)
  - 멀티 티커 지원: `--ticker NVDA,AAPL,MSFT`
  - 차트 타입 선택: `--chart standard/raindrop/multitf`
  - AI 분석 타입: `--analysis elliott/trend/support_resistance/none`
  - 백테스트 전략: `--backtest elliott_w3/ma_golden/rsi_oversold/none`
  - `--telegram`으로 통합 리포트 발송
- **Rich Telegram caption** — 검출 + AI 분석 + 백테스트 결과를 한 메시지에 통합
- **10 new pytest cases** (`tests/test_pipeline.py`)
  - Sibling discovery (env var / strict / unknown / not-found)
  - Smoke integration (실제 sibling 있을 때만 실행)
  - Caption formatter edge cases

### Verified (실측 동작 확인)
- **NVDA 180일 full pipeline**: 34 swings → 10 trendlines → 오버레이 차트(6 lines) → Elliott W3 백테스트 +29.87%
- **3-ticker batch** (NVDA/AAPL/MSFT): 각각 pattern detection + MA Golden 백테스트 병렬 실행
  - NVDA: no pattern / bt=+85.1%
  - AAPL: corrective/complete / bt=+19.5%
  - MSFT: impulse wave 5 (down!) / bt=+7.3%

### Rollback
복원 명령: `git checkout v0.1.0`

---

## [0.1.0] — 2026-04-18

### Added
- **Chart rendering 모듈** (`src/chart/`)
  - `data_loader.py`: yfinance 기반 OHLCV 로더, 5개 타임프레임(15m/1h/4h/daily/weekly) 지원
  - `data_loader.py`: 4h는 1h 데이터를 자동 리샘플링 (yfinance가 4h 직접 지원 안함)
  - `data_loader.py`: 멀티레벨 컬럼 자동 평탄화
  - `standard.py`: mplfinance 캔들스틱 + MA5/20/60/120 + 거래량 차트
  - `standard.py`: 트렌드라인/스윙 오버레이 지원 (`render_with_overlays`)
  - `multitf.py`: 1D + 4H + 15m 3층 합성 차트 (confluence 분석용)
  - `raindrop.py`: **Raindrop-like Volume Profile 차트** — TrendSpider Raindrop Chart의 무료 대체
  - `raindrop.py`: 가우시안 커널 기반 bar 내 거래량 분포 추정, 가로 폭으로 volume-at-price 시각화
- **Claude Vision analyzer** (`src/analyzer/`)
  - `vision.py`: 차트 PNG → base64 → Claude API → JSON 파싱
  - `vision.py`: tolerant JSON extraction (markdown fence, preamble, postscript 모두 처리)
  - `vision.py`: `analyze_chart()` 원샷 헬퍼 (로드→렌더→분석 end-to-end)
  - `prompts/elliott.md`: 엘리엇 파동 분석 시스템 프롬프트 (한국어)
  - `prompts/trend.md`: 추세 분석 프롬프트
  - `prompts/support_resistance.md`: 지지/저항 분석 프롬프트
- **Telegram notifier** (`src/notifier/`)
  - `telegram.py`: 차트 이미지 + 포맷팅된 분석 결과 동시 전송
  - `telegram.py`: 분석 타입별 자동 캡션 포맷팅 (Elliott/Trend)
  - `telegram.py`: 1024자 caption 제한 자동 처리
- **CLI 진입점** (`src/analyze.py`)
  - `python -m src.analyze --ticker NVDA --chart raindrop --type elliott --telegram`
  - `--no-ai` 옵션으로 차트만 렌더링
  - `--question`으로 커스텀 질의 가능
  - JSON 결과 자동 저장
- **Pytest 테스트 커버리지** (13개 테스트, 100% 통과)
  - Standard/Raindrop/Overlay 차트 렌더링
  - DataLoader 타임프레임 매핑 + 컬럼 정규화
  - JSON 파서 (fence / preamble / garbage input 모두 처리)

### Verified (실측 동작 확인)
- **NVDA 180일 표준 차트**: 129KB PNG, MA5/20/60/120 + 거래량 완벽 렌더링
- **NVDA 60일 Raindrop 차트**: 128KB PNG, 각 bar의 가로 굵기가 거래량 집중대를 정확히 시각화
- TrendSpider Raindrop Chart와 시각적 퀄리티 동등 수준 확인

### Rollback
복원하려면: `git checkout v0.0.0`

---

## [0.0.0] — 2026-04-18

### Added
- 프로젝트 초기화
- README with Quick Start + Emergency Rollback SOP
- CHANGELOG.md (Keep a Changelog 표준)
- .gitignore (Python 표준)
- requirements.txt (mplfinance, anthropic, python-telegram-bot, Pillow 포함)

### Context
- 목적: TrendSpider "Sidekick AI" 및 "Raindrop Chart" 기능의 무료 대체
- 기존 운영 시스템과 **완전 독립** — 기존 10개 레포 무접근
- Rollback 전략: archive 처리만으로 격리 가능

### Baseline
작업 시작 시점(2026-04-18) 기존 운영 10개 레포 commit SHA는
[backtest-lab CHANGELOG.md](https://github.com/jinhae8971/backtest-lab/blob/main/CHANGELOG.md)에 공통 기록.
