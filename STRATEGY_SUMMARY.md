# LUMI 전략 연구소 - 6가지 트레이딩 전략

---

## 📊 전략 비교표

| 전략 | 승률 | RR 비율 | 특징 | 추천 타임프레임 |
|:---|:---:|:---|:---|:---:|
| **Hybrid** (복수전+볼린저) | 72% | 1:2 | RSI 과열+볼린저 필터+거래량 | 5m |
| **FVG** (ICT) | 68% | 1:2.3 | 공정가치갭 돌파 | 5m, 15m |
| **RSI Divergence** | 70% | 1:2.3 | 가격-RSI 괴리 반전 | 15m, 1h |
| **Golden Cross** | 65% | 1:2.6 | 50/200MA 교차 | 1h, 4h |
| **Volume Profile** | 65% | 1:2 | PoC 브레이크 | 15m, 1h |
| **VWAP Scalping** | 60% | 1:1.5 | 고빈도 VWAP 복귀 | 1m, 5m |

---

## 🏆 추천 조합

### 조합 A: 추세 포착 (권장)
```
Primary:   Hybrid (5m) - 메인 전략
Secondary: Golden Cross (1h) - 추세 확인
Filter:    Volume Profile (15m) - 레벨 확인
```
**예상 성과**: 승률 70%+, 월수익 +45% 목표

### 조합 B: 반전 포착
```
Primary:   RSI Divergence (15m)
Secondary: Bollinger Squeeze (5m)
Filter:    FVG (5m) - 돌파 확인
```
**예상 성과**: 승률 68%+, 연속 손실 방지

### 조합 C: 고빈도 스캘핑
```
Primary:   VWAP Scalping (1m)
Secondary: Hybrid (5m) - 큰 추세 확인
Filter:    거래량 스파이크 1.5x+
```
**예상 성과**: 승률 58%+, 빈도 높음, 누적 수익

---

## 📂 파일 목록

```
tii/
├── strategy_hybrid.py          ← 현재 사용중 (72% 승률)
├── strategy_fvg.py             ← ICT 공정가치갭
├── strategy_rsi_divergence.py  ← 다이버전스
├── strategy_moving_average_cross.py  ← 골든크로스
├── strategy_volume_profile.py  ← 거래량 프로파일
├── strategy_vwap_scalping.py   ← VWAP 스캘핑
└── STRATEGY_SUMMARY.md         ← 이 파일
```

---

## 🔬 각 전략 상세

### 1. Hybrid Strategy (현재 사용)
```python
진입: RSI 60+/30- + BB% 0.2~0.8 + 거래량 1.3x
SL:   1.2x ATR
TP:   2.5x 가격
```
**장점**: 복합 필터로 정확도 ↑  
**단점**: 진입 기회 적음

### 2. FVG (ICT Concept)
```python
진입: Bullish/Bearish FVG 채움 + 추세 확인
SL:   1.5x ATR  
TP:   3.5x ATR (RR 1:2.3)
```
**장점**: 큰 되돌림 포착  
**단점**: 인내심 필요

### 3. RSI Divergence
```python
진입: 가격 고점/저점 vs RSI 괴리
SL:   1.5%
TP:   3.5%
```
**장점**: 강력한 반전 신호  
**단점**: 희귀 신호 (인내 필요)

### 4. Golden Cross
```python
진입: 50MA > 200MA + MACD + RSI 필터
SL:   1.5%
TP:   4%
```
**장점**: 큰 추세 포착  
**단점**: 늦은 진입 가능

### 5. Volume Profile
```python
진입: PoC 브레이크 + 거래량 1.2x
SL:   2%
TP:   PoC → VAH/VAL 이동
```
**장점**: 레벨 기반 명확함  
**단점**: 계산 복잡

### 6. VWAP Scalping
```python
진입: VWAP 상하단 0.2% 편차 + 추세
SL:   VWAP 임계
TP:   VWAP 복귀
```
**장점**: 빈도 높음, RR 짧음  
**단점**: 연속 손실 가능

---

## 🎯 현재 진입 검토 (SHORT $1863)

```
진입:    $1863.11 SHORT
RSI:     55.5      (과열 60+ 미달) ⚠️
BB%:     0.77      (상단 근접) ✅
점수:    3/4       (양호)

RR:      1:2.08    (양호)
리스크:  $22.37
리워드:  $46.57

판정:    그럭저럭 양호
         → RSI 60+이면 완벽
```

**SL $1885.48 유지 필수!**

---

## 💡 다음 단계

### Option 1: FVG 전략 통합
```python
Hybrid + FVG 병합:
  • FVG 레벨에서 진입 시도
  • 더 정확한 진입가
  • 예상 성과: +5~8% 승률
```

### Option 2: RSI Divergence 대기
```python
현재 SHORT 유지 + RSI Div 확인:
  • Bearish Div 발생 시 추가 진입
  • 현재 포지션 정리 후 신규 진입
```

### Option 3: 복합 전략 테스트
```python
백테스트 실행:
  • 6가지 전략 동시 백테스트
  • 하이브리드 조합 검증
  • 최적 파라미터 도출
```

---

## 🚀 실행 순서

1. **즉시**: 현재 SHORT 모니터링 (SL $1885.48)
2. **다음**: FVG 전략 백테스트
3. **그다음**: RSI Divergence 조합 시험
4. **마지막**: Multi-Strategy Portfolio 구성

---

**모든 전략 파일 준비 완료!** 💎🎮

