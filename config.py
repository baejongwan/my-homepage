# -*- coding: utf-8 -*-
"""
LUMI HYBRID PRO v2.0 - 개선 설정
적용일: 2026-02-23
개선사항: RSI 60+, FVG 확인, 15분 추세 필수
"""

import os
from dotenv import load_dotenv

load_dotenv()

# [1] API 설정
IS_LIVE_TRADING = True
EXCHANGE_NAME = 'binance'

# 다양한 API 키 이름 지원
API_KEY = os.getenv('API_KEY') or os.getenv('BINANCE_API_KEY', '')
SECRET_KEY = os.getenv('SECRET_KEY') or os.getenv('BINANCE_SECRET', '') or os.getenv('BINANCE_API_SECRET', '')

# [2] 거래 설정 - HYBRID PRO v2.0
SYMBOL = "ETH/USDT"
TIMEFRAMES = ['5m']  # 메인 타임프레임 (5분)
TF_15M = '15m'       # 추세 확인용 (필수화)
LIMIT = 200

# [3] 시간 설정
CHECK_INTERVAL = 1      # 1초 체크
REPORT_INTERVAL = 60    # 1분 리포트
ORDER_WAIT = 2          # 주문 대기
MAX_RETRIES = 50

# [4] 자금 관리
LEVERAGE = 20
ENTRY_PERCENT = 25    # 100% 투자
INIT_BALANCE = 111      # 폴백값
TRADING_FEE_RATE = 0.0005

AUTO_BALANCE_MODE = True
BALANCE_FEE_BUFFER = 5.0
MIN_BALANCE_USDT = 50

# [SAFETY] 리스크 관리
MAX_DAILY_LOSS_PERCENT = 10
MAX_CONSECUTIVE_LOSSES = 3
MIN_ORDER_SIZE_USDT = 25  # Binance 최소 $20, 안전마진 $25
POSITION_TIMEOUT_BARS = 12

# [5] HYBRID PRO v2.0 파라미터 (개선됨)
# RSI 설정 - SHORT 과열 55→60 상향
RSI_LONG_THRESHOLD = 30      # LONG: RSI 30- 과매도
RSI_SHORT_THRESHOLD = 60     # SHORT: RSI 60+ 과열 (개선: 55→60)

# 볼린저 설정 - 범위 확장
BB_PCT_B_LOW = 0.15          # 하단 확장 (0.2→0.15)
BB_PCT_B_HIGH = 0.85         # 상단 확장 (0.8→0.85)
BB_BANDWIDTH_MIN = 0.03      # 최소 밴드폭 (Squeeze 제외)

# 거래량 설정
VOLUME_MULTIPLIER = 1.3      # 1.3배 이상

# SL/TP (황금비율)
SL_PERCENT = 0.012           # 1.2%
TP_PERCENT = 0.025           # 2.5%

# [NEW] v2.0 필수 설정
TREND_15M_REQUIRED = True      # 15분 추세 확인 필수화
FVG_FILTER_ENABLED = True      # FVG 레벨 확인 활성화

# [NEW] v2.1 상승장 추세 추종 모드
MARKET_MODE_AUTO = True        # 자동 시장 판별 활성화
TREND_FOLLOW_ENABLED = True    # 추세 추종 모드 활성화

# 추세 추종 모드 설정
TF_RSI_MIN = 50               # 추세 추종: RSI 최소 50
TF_RSI_MAX = 70               # 추세 추종: RSI 최대 70 (과열 제외)
TF_BB_PCT_MIN = 0.40          # 추세 추종: BB% 최소 0.4
TF_BB_PCT_MAX = 0.80          # 추세 추종: BB% 최대 0.8
TF_VOLUME_MULT = 1.2          # 추세 추종: 거래량 1.2배

# [6] 거래량 (기존 포지션 감지용)
SIZE = 0.052  # 기본 거래량 (ETH)

# [NEW] v2.1 트렌드 추종 모드 설정
TREND_FOLLOW_ENABLED = True
TF_RSI_MIN = 50               # 추세 추종: RSI 최소 50
TF_RSI_MAX = 70               # 추세 추종: RSI 최대 70 (과열 제외)
TF_BB_PCT_MIN = 0.40          # 추세 추종: BB% 최소 0.4
TF_BB_PCT_MAX = 0.80          # 추세 추종: BB% 최대 0.8
TF_VOLUME_MULT = 1.2          # 추세 추종: 거래량 1.2배
TF_TP_PERCENT = 0.035         # 추세 모드 TP: 3.5% (더 큰 목표)

# [7] 텔레그램 설정
TELEGRAM_ENABLED = True
TELEGRAM_BOT_TOKEN = "8057776330:AAH-eE6MILL_spHztG8eUG1tjjw5YrmeXqg"
TELEGRAM_CHAT_ID = "8074909196"

# [8] 파일 경로
LOG_FILE = "trade_log_v2.csv"
REPORT_FILE = "trade_summary_v2.txt"

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1)

print("[OK] HYBRID PRO v2.1 설정 로드 완료")
print(f"   RSI LONG (반전): {RSI_LONG_THRESHOLD}")
print(f"   RSI LONG (추세): {TF_RSI_MIN}~{TF_RSI_MAX}")
print(f"   RSI SHORT: {RSI_SHORT_THRESHOLD}")
print(f"   15분 추세: {'필수' if TREND_15M_REQUIRED else '선택'}")
print(f"   FVG 필터: {'활성화' if FVG_FILTER_ENABLED else '비활성화'}")
print(f"   듀얼 모드: {'활성화' if TREND_FOLLOW_ENABLED else '비활성화'}")
