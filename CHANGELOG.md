# Changelog

All notable changes to **chart-analyzer** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- trendline-detector와 통합 (swing/trendline 오버레이 자동 적용)
- 여러 티커 배치 분석 + Telegram 요약
- Claude opus-4-7 모델 자동 폴백 로직
- GitHub Actions workflow_dispatch 트리거

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
