# Changelog

All notable changes to **chart-analyzer** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- mplfinance 기반 표준 차트 렌더링 (OHLCV + MA5/20/60/120)
- Claude Vision API 통합 (`claude-opus-4-7`)
- 멀티 타임프레임 차트 합성 (1D + 4H + 15m)
- Raindrop-like Volume Profile 차트 (TrendSpider Raindrop 대체)
- Telegram bot 이미지 + 분석 결과 동시 발송
- GitHub Actions on-demand 실행 (workflow_dispatch)

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
