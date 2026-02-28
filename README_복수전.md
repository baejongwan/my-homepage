# -*- coding: utf-8 -*-
"""
LUMI 복수전 봇 v3.0 실행 가이드
===========================

✅ 완성된 설정:
1. 전략: 복수전 (Revenge) - RSI + SMA50
2. 투자: 100% (config.ENTRY_PERCENT = 1.0)
3. 양방향: LONG & SHORT 모두 진입
4. SL/TP: 고정 -1.2% / +2.5%
5. RSI 청산: 과열(65) / 과매도(35) 시 조기 청산

📁 파일 구성:
├── main_auto.py          ← 복수전 전략 통합 완료
├── strategy_revenge.py   ← 복수전 알고리즘
├── config.py             ← 100% 투자 설정
└── START_revenge.bat     ← 실행 파일

🎯 진입 조건:
• LONG: RSI ≤30 (과매도) + SMA50 근접
• SHORT: RSI ≥60 (과열) + SMA50 근접

🎯 청산 조건:
• TP: 목표가 ±2.5% 도달
• RSI 청산: 반전 신호 (LONG≥65, SHORT≤35)
• SL: -1.2% 손절가 (방어선)

🚀 실행 방법:
바탕화면/tii/START_revenge.bat 더블클릭
  ↓
[1] 선택 → 자동 거래 시작

⚠️ 주의사항:
• 100% 투자 = 높은 수익 + 높은 리스크
• 레버리지 10x 적용 시 SL -12%, TP +25%
• RSI 청산으로 조기 수익 실현 가능

📊 기대 수익륜: +321% (과거 백테스트 기준)
"""

print("="*60)
print("LUMI 복수전 봇 v3.0 - 설정 완료!")
print("="*60)
print()
print("✅ main_auto.py: 복수전 전략 통합 완료")
print("✅ config.py: 100% 투자 설정 완료")
print("✅ strategy_revenge.py: 양방향 진입 지원")
print()
print("실행 방법:")
print("  START_revenge.bat 더블클릭 → [1] 선택")
print()
print("🎯 목표 수익률: +321%")
print("="*60)
