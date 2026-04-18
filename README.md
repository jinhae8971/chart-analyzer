# 📊 chart-analyzer

차트 이미지 생성 + Claude Vision 기반 차트 분석 시스템.
TrendSpider의 "Sidekick AI" 기능을 무료로 대체하는 프로젝트.

## 🎯 목적

- 주어진 티커에 대해 **mplfinance로 전문가급 차트 PNG 생성**
- Claude Vision API로 **"이 차트의 엘리엇 파동 분석해줘"** 등 자연어 질의
- **Raindrop-like Volume Profile** 차트 (TrendSpider 고유 Raindrop Chart 대체)
- Telegram으로 분석 결과 + 차트 이미지 즉시 전송

## 📦 기술 스택

- **mplfinance** — 금융 차트 시각화 (OHLCV, 지표, volume profile)
- **yfinance / FinanceDataReader** — 무료 시장 데이터
- **anthropic** — Claude Vision (`claude-opus-4-7` 또는 `claude-sonnet-4-6`)
- **python-telegram-bot** — 알림 전송
- **Pillow** — 이미지 후처리 (multi-timeframe 합성)

## 🚀 Quick Start

```bash
git clone https://github.com/jinhae8971/chart-analyzer.git
cd chart-analyzer
pip install -r requirements.txt

# 환경변수 설정
export ANTHROPIC_API_KEY="sk-ant-..."
export TELEGRAM_BOT_TOKEN="8481005106:..."
export TELEGRAM_CHAT_ID="954137156"

# 단일 종목 분석
python -m src.analyze --ticker NVDA --timeframe daily --question "현재 엘리엇 파동 위치 분석해줘"

# Raindrop-like volume profile 차트
python -m src.raindrop --ticker NVDA --days 60
```

## 📂 프로젝트 구조

```
chart-analyzer/
├── src/
│   ├── chart/           # 차트 렌더링 (mplfinance 기반)
│   │   ├── standard.py     # 표준 OHLCV + MA
│   │   ├── multitf.py      # 멀티 타임프레임 합성 (1D/4H/15m)
│   │   └── raindrop.py     # Volume Profile (Raindrop Chart 대체)
│   ├── analyzer/        # Claude Vision 분석
│   │   ├── vision.py       # 차트 이미지 → Claude → JSON 해석
│   │   └── prompts/        # 시장별 분석 프롬프트
│   ├── notifier/
│   │   └── telegram.py     # 이미지 + 텍스트 전송
│   └── analyze.py       # CLI 진입점
├── configs/
├── tests/
├── .github/workflows/
├── CHANGELOG.md
├── README.md
└── requirements.txt
```

## 💡 핵심 활용 예시

### 1. 단일 차트 분석
```python
from src.analyzer import analyze_chart

result = analyze_chart(
    ticker="NVDA",
    timeframe="daily",
    question="현재 엘리엇 파동 3파 진입 가능한 위치인지 판단해줘",
)
# result: {'answer': '...', 'confidence': 0.78, 'key_levels': {...}}
```

### 2. 멀티 타임프레임 Confluence
```python
# 1D(trend) + 4H(swing) + 15m(entry) 3개 차트를 한 이미지로 합성
# → Claude Vision이 "3개 타임프레임에서 컨플루언스 있는지" 판단
```

### 3. Raindrop-like Volume Profile
```python
# Volume-weighted price distribution → 기관 평균 매집가 시각화
# TrendSpider의 Raindrop Chart 고유 기능을 오픈소스 대체
```

## 🔄 Emergency Rollback

### 이전 버전으로 즉시 복원
```bash
git log --oneline
git checkout <commit_sha>
```

### 이 레포가 문제될 경우
이 레포는 **완전 독립** (Python 라이브러리 호출만). archive 처리로 격리 가능.
**기존 10개 운영 레포에는 어떤 영향도 미치지 않습니다.**

## 📝 변경 이력

[CHANGELOG.md](./CHANGELOG.md) 참조

## 🔗 관련 프로젝트

- [global-market-orchestrator](https://github.com/jinhae8971/global-market-orchestrator)
- [backtest-lab](https://github.com/jinhae8971/backtest-lab)
- [trendline-detector](https://github.com/jinhae8971/trendline-detector)

## 📜 License

Personal use — jinhae8971
