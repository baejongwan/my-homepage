# -*- coding: utf-8 -*-
"""
modules/strategy.py - 듀얼 모드 전략 (반전 + 추세 추종)
향상된 청산 로직: 동적 드래그 스탑 + TP 확장
"""

import numpy as np


class StrategyEngine:
    """HYBRID PRO v2.3 듀얼 모드 전략 엔진"""
    
    def __init__(self, config=None):
        self.config = config or {}
        
        # 기본 설정값
        self.rsi_long = config.get('RSI_LONG_THRESHOLD', 30)
        self.rsi_short = config.get('RSI_SHORT_THRESHOLD', 60)
        self.bb_low = config.get('BB_PCT_B_LOW', 0.15)
        self.bb_high = config.get('BB_PCT_B_HIGH', 0.85)
        
        # 추세 추종 모드
        self.tf_rsi_min = config.get('TF_RSI_MIN', 50)
        self.tf_rsi_max = config.get('TF_RSI_MAX', 70)
        self.tf_bb_min = config.get('TF_BB_PCT_MIN', 0.40)
        self.tf_bb_max = config.get('TF_BB_PCT_MAX', 0.80)
        
        # SL/TP
        self.sl_pct = config.get('SL_PERCENT', 0.012)
        self.tp_pct = config.get('TP_PERCENT', 0.025)
        self.tf_tp_pct = config.get('TF_TP_PERCENT', 0.035)
        
        # 🆕 동적 드래그 스탑 설정
        self.trailing_profit_per_step = 1.0  # 1% 단위로
        self.trailing_lock_ratio = 0.5       # 50%씩 잠금 (1% → 0.5%, 2% → 1%)
        self.min_trailing_start = 1.0        # 1%부터 시작
        
        # 🆕 TP 확장 설정
        self.tp_extend_threshold = 0.3       # 목표 TP의 70% 도달 시 (0.7)
        self.tp_extend_amount = 0.005        # 0.5%씩 확장
        self.current_extended_tp = {}        # 포지션별 확장된 TP 저장
        
        # 🆕 드래그 스탑 추적 (최고 수익 기록 - 버그 수정)
        self.peak_profit_tracker = {}      # {'LONG': peak_pnl, 'SHORT': peak_pnl}
        
        # 🆕 시간대 기반 조건 (루미 분석 기반)
        self.night_rsi_threshold = 28      # 야간 롱: RSI < 28
        self.night_bb_threshold = 0.15     # 야간 롱: BB% < 0.15
        self.short_force_rsi = 65          # 강제 숏: RSI > 65
        self.short_force_bb = 0.75         # 강제 숏: BB% > 0.75
    
    def check_night_long_conditions(self, market_state):
        """
        🆕 야간 롱 진입 조건 확인 (루미 분석 기반)
        
        Returns:
            (bool, str): (허용 여부, 사유)
        """
        if market_state is None:
            return False, "데이터 없음"
        
        rsi = market_state.get('rsi', 50)
        bb_pct = market_state.get('bb_pct', 0.5)
        
        # 극과매도 구간만 허용
        if rsi < self.night_rsi_threshold and bb_pct < self.night_bb_threshold:
            return True, f"극과매도 (RSI {rsi:.1f} < {self.night_rsi_threshold}, BB% {bb_pct:.2f} < {self.night_bb_threshold})"
        
        return False, f"RSI {rsi:.1f}, BB% {bb_pct:.2f} (극과매도 아님)"
    
    def check_enhanced_short_signal(self, market_state):
        """
        🆕 강화된 숏 진입 조건 (루미 분석 기반)
        
        Returns:
            (bool, str): (진입 여부, 사유)
        """
        if market_state is None:
            return False, "데이터 없음"
        
        rsi = market_state.get('rsi', 50)
        bb_pct = market_state.get('bb_pct', 0.5)
        
        # 과매수 강제 진입 조건
        if rsi > self.short_force_rsi and bb_pct > self.short_force_bb:
            return True, f"과매수 돌파 (RSI {rsi:.1f} > {self.short_force_rsi}, BB% {bb_pct:.2f} > {self.short_force_bb})"
        
        return False, f"RSI {rsi:.1f}, BB% {bb_pct:.2f} (과매수 아님)"
    
    def determine_mode(self, market_state):
        """현재 모드 판단 (반전 vs 추세)"""
        rsi = market_state.get('rsi', 50)
        return 'TREND' if rsi >= 50 else 'REVERSAL'
    
    def check_long_signal(self, market_state, df=None):
        """롱 진입 신호 확인"""
        if market_state is None:
            return False, "시장 데이터 없음"
        
        rsi = market_state.get('rsi', 50)
        bb_pct = market_state.get('bb_pct', 0.5)
        trend = market_state.get('trend', 'NEUTRAL')
        mode = self.determine_mode(market_state)
        
        checks = []
        
        # 모드별 조건
        if mode == 'REVERSAL':
            # 반전 모드: RSI < 30, BB% 0.15-0.6
            if rsi < self.rsi_long:
                checks.append(f"RSI 과매도: {rsi:.1f}")
            if self.bb_low <= bb_pct <= 0.6:
                checks.append(f"BB% 과매도: {bb_pct:.2f}")
            if trend == 'DOWN':
                checks.append(f"추세 하강")
            
            if len(checks) >= 2:
                return True, f"반전 롱 ({', '.join(checks)})"
                
        else:
            # 추세 추종 모드: RSI 50-70, BB% 0.4-0.8, 상승 추세
            if self.tf_rsi_min <= rsi <= self.tf_rsi_max:
                checks.append(f"RSI 추세: {rsi:.1f}")
            if self.tf_bb_min <= bb_pct <= self.tf_bb_max:
                checks.append(f"BB% 추세: {bb_pct:.2f}")
            if trend == 'UP':
                checks.append(f"추세 상승")
            
            if len(checks) >= 2:
                return True, f"추세 롱 ({', '.join(checks)})"
        
        return False, f"대기 중 ({len(checks)}/3)"
    
    def check_short_signal(self, market_state, df=None):
        """숏 진입 신호 확인"""
        if market_state is None:
            return False, "시장 데이터 없음"
        
        rsi = market_state.get('rsi', 50)
        bb_pct = market_state.get('bb_pct', 0.5)
        trend = market_state.get('trend', 'NEUTRAL')
        mode = self.determine_mode(market_state)
        
        checks = []
        
        if mode == 'REVERSAL':
            # 반전 모드: RSI > 70, BB% > 0.7
            if rsi > self.rsi_short:
                checks.append(f"RSI 과매수: {rsi:.1f}")
            if bb_pct > 0.7:
                checks.append(f"BB% 과매수: {bb_pct:.2f}")
            if trend == 'UP':
                checks.append(f"추세 상승")
            
            if len(checks) >= 2:
                return True, f"반전 숏 ({', '.join(checks)})"
                
        else:
            # 추세 추종 모드 - 롱과 대칭되게 2개 조건으로 수정
            ema8 = market_state.get('ema8', 0)
            ema21 = market_state.get('ema21', 0)
            
            if self.tf_rsi_min <= rsi <= self.tf_rsi_max:
                checks.append(f"RSI 추세: {rsi:.1f}")
            if self.tf_bb_min <= bb_pct <= self.tf_bb_max:
                checks.append(f"BB% 추세: {bb_pct:.2f}")
            if ema8 < ema21:
                checks.append(f"EMA 하강")
            
            if len(checks) >= 2:
                return True, f"추세 숏 ({', '.join(checks)})"
        
        return False, f"대기 중 ({len(checks)}/3)"
    
    def calculate_sl_tp(self, entry_price, side, mode='REVERSAL'):
        """SL/TP 가격 계산"""
        if mode == 'TREND':
            tp_pct = self.tf_tp_pct
        else:
            tp_pct = self.tp_pct
        
        if side == 'LONG':
            sl = entry_price * (1 - self.sl_pct)
            tp = entry_price * (1 + tp_pct)
        else:
            sl = entry_price * (1 + self.sl_pct)
            tp = entry_price * (1 - tp_pct)
        
        return sl, tp, tp_pct
    
    def calculate_dynamic_sl(self, entry_price, market_state, pnl_pct=0):
        """
        🆕 하이브리드 동적 손절가 계산
        
        1. 변동성 기준 (볼린저 밴드폭)
        2. 추세 강도 기준
        3. 수익 누적 기반 (드래그)
        
        0.5% 단위로 수익 잠금
        """
        if market_state is None:
            return self.sl_pct  # 기본값 반환
        
        # 1️⃣ 변동성 기준
        bb_width = market_state.get('bb_width', 0.04)
        if bb_width < 0.03:      # 좁은 밴드 = 저변동성
            base_sl = 0.006      # 타이트 SL
        elif bb_width > 0.06:    # 넓은 밴드 = 고변동성
            base_sl = 0.012      # 여유 SL
        else:
            base_sl = 0.008      # 중간
        
        # 2️⃣ 추세 강도 기준
        ema8 = market_state.get('ema8', 0)
        ema21 = market_state.get('ema21', 0)
        
        if ema8 > 0 and ema21 > 0:
            trend_strength = abs(ema8 - ema21) / ema21
            
            if trend_strength > 0.02:    # 강한 추세
                trend_factor = 1.2 if pnl_pct > 0 else 0.8  # 수익중엔 여유, 손실중엔 타이트
            elif trend_strength < 0.005:  # 횡보/약한 추세
                trend_factor = 0.8         # 타이트
            else:
                trend_factor = 1.0
        else:
            trend_factor = 1.0
        
        sl_pct = base_sl * trend_factor
        
        # 3️⃣ 🎯 수익 누적 기반 드래그 (0.5% 단위)
        # +0.5% → 0% (본전)
        # +1.0% → 0.5% 잠금
        # +1.5% → 1.0% 잠금
        # +2.0% → 1.5% 잠금
        if pnl_pct >= 0.5:
            # 수익의 0.5% 아래로 SL 설정 (예: 1.2% 수익 → SL=0.7%)
            trailing_sl = max(0, pnl_pct - 0.5) / 100
            # 기본 SL과 비교해서 더 높은 값 선택 (안전장치)
            sl_pct = max(trailing_sl, min(sl_pct, 0.015))
            
            # 디버그 로그
            print(f"   🎯 수익 기반 SL: 수익 {pnl_pct:.2f}% → SL {sl_pct*100:.2f}%")
        
        # 안전 범위 제한 (0.5% ~ 1.5%)
        return max(0.005, min(0.015, sl_pct))  # 0.5% ~ 1.5% 사이
        
    def calculate_dynamic_sl_price(self, entry_price, side, market_state, pnl_pct=0):
        """
        동적 SL 가격 계산
        """
        sl_pct = self.calculate_dynamic_sl(entry_price, market_state, pnl_pct)
        
        if side == 'LONG':
            return entry_price * (1 - sl_pct)
        else:
            return entry_price * (1 + sl_pct)
    
    def _calculate_dynamic_trailing_stop(self, entry_price, current_price, pnl_pct, position):
        """
        동적 드래그 스탑 계산 (수정됨: 최고점 기준)
        원칙: 한번 1% 넘으면 그 기준으로 스탑 고정. 수익 떨어져도 유지.
        예: 최고 1.3% → 0.5% 보장. (1.3% -> 진입까지 떨어져도 0.5%에서 청산)
        """
        # 🆕 최고 수익 기록 업데이트
        if pnl_pct > self.peak_profit_tracker.get(position, 0):
            self.peak_profit_tracker[position] = pnl_pct
            if pnl_pct >= self.min_trailing_start:
                print(f"   📈 최고 수익 갱신: {pnl_pct:.2f}% (드래그 스탑 활성화)")
        
        peak_pnl = self.peak_profit_tracker.get(position, 0)
        
        # 최고 수익이 시작 임계값 미만이면 동작 안함
        if peak_pnl < self.min_trailing_start:
            return None
        
        # 🆕 동적 잠금 계산 (개선된 방식: 수익 - 0.8% - 더 여유있게)
        # 예: 1.0%수익 → 0.2%잠금, 1.8%수익 → 1.0%잠금, 2.0%수익 → 1.2%잠금
        locked_profit = max(0.3, peak_pnl - 0.8)  # 최소 0.3% 보장 (이전 0.5%)
        
        if position == 'LONG':
            # 롱: 진입가 + 잠금 수익% 에서 스탑
            stop_price = entry_price * (1 + locked_profit / 100)
            # 현재가가 스탑보다 낮거나 같으면 청산
            if current_price <= stop_price:
                return {
                    'action': 'TS',
                    'reason': f"TS (드래그 스탑 +{locked_profit}% 보장, 최고 {peak_pnl:.2f}%)",
                    'stop_price': stop_price,
                    'locked_profit': locked_profit,
                    'peak_pnl': peak_pnl
                }
        else:
            # 숏: 진입가 - 잠금 수익% 에서 스탑
            stop_price = entry_price * (1 - locked_profit / 100)
            if current_price >= stop_price:
                return {
                    'action': 'TS',
                    'reason': f"TS (드래그 스탑 +{locked_profit}% 보장, 최고 {peak_pnl:.2f}%)",
                    'stop_price': stop_price,
                    'locked_profit': locked_profit,
                    'peak_pnl': peak_pnl
                }
        
        return None
    
    def _check_tp_extension(self, entry_price, current_price, base_tp, pnl_pct, market_state, position_key):
        """
        TP 확장 검사: 목표에 근접했지만 추세가 유리하면 TP 연장
        """
        if market_state is None:
            return None, base_tp
        
        # 기본 TP% 계산
        base_tp_pct = abs((base_tp - entry_price) / entry_price)
        current_progress = abs(pnl_pct) / 100
        
        # 목표 진행률 (예: TP 2.5%일 때 70% 도달 = 1.75% 수익)
        progress_to_tp = current_progress / base_tp_pct if base_tp_pct > 0 else 0
        
        # 70% 이상 도달했고, 아직 확장하지 않았으면 검토
        if progress_to_tp >= (1 - self.tp_extend_threshold):
            rsi = market_state.get('rsi', 50)
            trend = market_state.get('trend', 'NEUTRAL')
            
            # 롱에서 여전히 강한 상승 추세면 TP 확장
            if position_key == 'LONG':
                if rsi >= 60 and trend == 'UP':  # 여전히 강한 추세
                    new_tp = base_tp * (1 + self.tp_extend_amount)
                    return f"TP확장 (+{self.tp_extend_amount*100:.1f}%)", new_tp
            
            # 숏에서 여전히 강한 하� 추세면 TP 확장
            elif position_key == 'SHORT':
                if rsi <= 40 and trend == 'DOWN':
                    new_tp = base_tp * (1 - self.tp_extend_amount)
                    return f"TP확장 (-{self.tp_extend_amount*100:.1f}%)", new_tp
        
        return None, base_tp
    
    def should_exit(self, position, entry_price, current_price, market_state=None):
        """
        청산 여부 확인 (향상된 로직)
        
        체크 순서:
        1. 기본 SL (손절)
        2. 동적 드래그 스탑 (수익 잠금)
        3. TP 확장 검사
        4. 기본 TP 체크
        5. 추세 반전 보호 (수익 중)
        6. 고점/저점 꺾임 보호
        """
        if not position or not entry_price:
            return None, 0
        
        direction = 1 if position == 'LONG' else -1
        pnl_pct = (current_price / entry_price - 1) * 100 * direction
        
        # 1️⃣ 기본 SL(손절) 체크 (최우선)
        if position == 'LONG' and current_price <= entry_price * (1 - self.sl_pct):
            return 'SL (기본 손절)', pnl_pct
        if position == 'SHORT' and current_price >= entry_price * (1 + self.sl_pct):
            return 'SL (기본 손절)', pnl_pct
        
        # 🆕 2️⃣ 동적 드래그 스탑 체크 (항상 체크 - 내부에서 최고점 기준으로 판단)
        ts_result = self._calculate_dynamic_trailing_stop(
            entry_price, current_price, pnl_pct, position
        )
        if ts_result:
            return ts_result['reason'], pnl_pct
        
        # 드래그 스탑 활성화되어 있으면 스탑가 표시 (디버그)
        peak_pnl = self.peak_profit_tracker.get(position, 0)
        if peak_pnl >= self.min_trailing_start:
            locked_profit = (peak_pnl // self.trailing_profit_per_step) * self.trailing_lock_ratio
            if position == 'LONG':
                stop_price = entry_price * (1 + locked_profit / 100)
                print(f"   🛡️ 드래그 스탑 감시 중: 현재 {pnl_pct:.2f}% / 최고 {peak_pnl:.2f}% / 스탑가 ${stop_price:.2f}")
            else:
                stop_price = entry_price * (1 - locked_profit / 100)
                print(f"   🛡️ 드래그 스탑 감시 중: 현재 {pnl_pct:.2f}% / 최고 {peak_pnl:.2f}% / 스탑가 ${stop_price:.2f}")
        
        # 기본 TP 가격 계산
        base_tp_pct = self.tf_tp_pct if self.determine_mode(market_state or {}) == 'TREND' else self.tp_pct
        if position == 'LONG':
            base_tp = entry_price * (1 + base_tp_pct)
        else:
            base_tp = entry_price * (1 - base_tp_pct)
        
        # 🆕 3️⃣ TP 확장 검사 (목표에 근접하고 추세 유리하면)
        if market_state and pnl_pct > 0:
            extension_reason, adjusted_tp = self._check_tp_extension(
                entry_price, current_price, base_tp, pnl_pct, market_state, position
            )
            if extension_reason:
                # TP 확장됨 - 로그용 정보 반환 (체크 계속)
                print(f"   💡 {extension_reason}: 새로운 TP ${adjusted_tp:.2f}")
                base_tp = adjusted_tp
        
        # 기본 TP vs 확장된 TP 중 더 높은/낮은 값 사용
        tp = base_tp
        
        # 4️⃣ 기본 TP(익절) 체크
        if position == 'LONG' and current_price >= tp:
            return 'TP (목표 익절)', pnl_pct
        if position == 'SHORT' and current_price <= tp:
            return 'TP (목표 익절)', pnl_pct
        
        # 5️⃣ [루미 설계] 추세 반전 보호 (수익이 1.0% 이상일 때만 발동)
        if pnl_pct >= 1.0 and market_state:
            ema8 = market_state.get('ema8', 0)
            ema21 = market_state.get('ema21', 0)
            rsi = market_state.get('rsi', 50)
            trend = market_state.get('trend', 'NEUTRAL')
            
            print(f"   🔍 PG 체크: EMA8(${ema8:.2f}) vs EMA21(${ema21:.2f}), 추세={trend}, RSI={rsi:.1f}")
            
            # [필터 A] 추세 반전 (이평선 교차)
            if position == 'LONG' and ema8 < ema21:
                print(f"   ⚠️ 데드크로스 감지! EMA8 < EMA21 → PG 청산")
                return 'PG (추세 반전 보호)', pnl_pct
            if position == 'SHORT' and ema8 > ema21:
                print(f"   ⚠️ 골든크로스 감지! EMA8 > EMA21 → PG 청산")
                return 'PG (추세 반전 보호)', pnl_pct
            
            # [필터 B] 추세 반전 보조 확인 (여전히 유리한 추세인지)
            if position == 'LONG' and trend == 'DOWN':
                print(f"   ⚠️ 롱 포지션 하락 추세 전환 → PG 청산")
                # 상승 중인데 하락 추세로 바뀜
                return 'PG (숏 추세 전환)', pnl_pct
            if position == 'SHORT' and trend == 'UP':
                print(f"   ⚠️ 숏 포지션 상승 추세 전환 → PG 청산")
                return 'PG (롱 추세 전환)', pnl_pct
        
        # 6️⃣ 고점/저점 꺾임 보호
        if pnl_pct >= 1.5 and market_state:
            rsi = market_state.get('rsi', 50)
            ema8 = market_state.get('ema8', 0)
            
            if position == 'LONG' and rsi > 70 and current_price < ema8:
                return 'PG (과매수 꺾임)', pnl_pct
            if position == 'SHORT' and rsi < 30 and current_price > ema8:
                return 'PG (과매도 반등)', pnl_pct
        
        return None, pnl_pct
    
    def reset_position_tracking(self, position):
        """포지션 종료 시 추적 데이터 초기화"""
        if position in self.peak_profit_tracker:
            del self.peak_profit_tracker[position]
            print(f"   🔄 {position} 포지션 추적 데이터 초기화 완료")
