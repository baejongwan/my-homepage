# -*- coding: utf-8 -*- qkswjs
"""
LUMI HYBRID PRO v2.1 - 모듈화 버전
듀얼 모드 (반전 + 추세 추종) + 자기학습 시스템

[구조]
- main.py: 메인 오케스트레이터 (간결함)
- modules/: 기능별 모듈 폴더
  - exchange.py: 거래소 연결, 잔고, 레버리지
  - strategy.py: 듀얼 모드 전략 (신호 생성)
  - executor.py: 주문 실행 (롱/숏/청산)
  - position.py: 포지션 상태 관리
  - market_data.py: 데이터 조회 및 지표
  - notifier.py: 텔레그램 알림
  - utils.py: 유틸리티 함수

작성: 루미 (2026-02-25)
버전: v2.1.1 모듈화
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

import time
from datetime import datetime
import os

# 설정 로드
from config import *

# 모듈 임포트
from modules import (
    ExchangeManager,
    StrategyEngine,
    OrderExecutor,
    PositionManager,
    MarketDataProvider,
    TelegramNotifier,
    safe_float
)

# 데이터 수집 시스템 (있으면 로드)
try:
    from data_collector import DataCollector
    from self_learning import SelfLearningSystem
    DATA_COLLECTION_ENABLED = True
except ImportError:
    DATA_COLLECTION_ENABLED = False


class TradingBot:
    """메인 트레이딩 봇 - 모듈화 버전"""
    
    def __init__(self):
        self.config = self._load_config()
        
        # 모듈 초기화
        self.exchange_mgr = ExchangeManager(
            symbol=self.config['SYMBOL'],
            leverage=self.config['LEVERAGE']
        )
        
        self.strategy = StrategyEngine(self.config)
        self.position_mgr = PositionManager(history_file="logs/trade_history.json")
        self.market_data = MarketDataProvider(symbol=self.config['SYMBOL'])
        
        self.notifier = TelegramNotifier(
            self.config.get('TELEGRAM_BOT_TOKEN', ''),
            self.config.get('TELEGRAM_CHAT_ID', '')
        )
        
        self.executor = OrderExecutor(
            self.exchange_mgr,
            self.config,
            self.notifier
        )
        
        # 데이터 수집
        self.data_collector = None
        self.learner = None
        if DATA_COLLECTION_ENABLED:
            try:
                self.data_collector = DataCollector()
                self.learner = SelfLearningSystem()
                print("✅ 데이터 수집 시스템 로드 완료")
            except Exception as e:
                print(f"⚠️ 데이터 수집 시스템 로드 실패: {e}")
        
        # 상태 변수
        self.last_check = 0
        self.last_report = 0
        self.running = True
        
        # 🎯 연속 신호 확인 (2~3회)
        self.signal_confirmation = 2  # 2회 연속 신호 필요
        self.long_signal_count = 0
        self.short_signal_count = 0
        self.last_signal_price = 0
        self.max_signal_price_diff = 5.0  # $5 이내 가격 변화만 동일 신호로 인정
        
        # 🆕 청산 후 쿨다운 (TS 청산 후 바로 재진입 방지)
        self.exit_cooldown_until = 0  # 타임스탬프 (초)
        self.exit_cooldown_minutes = 3  # 최소 3분 대기
        self.last_exit_time = None
        self.last_exit_reason = None
        self.last_exit_pnl = 0
    
    def _load_config(self):
        """설정값 로드"""
        return {
            'SYMBOL': SYMBOL,
            'TIMEFRAMES': getattr(self, 'TIMEFRAMES', ['5m']),
            'LEVERAGE': LEVERAGE,
            'SL_PERCENT': SL_PERCENT,
            'TP_PERCENT': TP_PERCENT,
            'TF_TP_PERCENT': TF_TP_PERCENT,
            'MIN_ORDER_SIZE_USDT': getattr(self, 'MIN_ORDER_SIZE_USDT', 25),
            'RSI_LONG_THRESHOLD': RSI_LONG_THRESHOLD,
            'RSI_SHORT_THRESHOLD': RSI_SHORT_THRESHOLD,
            'BB_PCT_B_LOW': BB_PCT_B_LOW,
            'BB_PCT_B_HIGH': BB_PCT_B_HIGH,
            'TF_RSI_MIN': TF_RSI_MIN,
            'TF_RSI_MAX': TF_RSI_MAX,
            'TF_BB_PCT_MIN': TF_BB_PCT_MIN,
            'TF_BB_PCT_MAX': TF_BB_PCT_MAX,
            'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
            'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
            'CHECK_INTERVAL': CHECK_INTERVAL,
            'REPORT_INTERVAL': REPORT_INTERVAL
        }
    
    def log(self, msg, telegram=False, error=False):
        """로그 출력"""
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = "❌" if error else "✅"
        print(f"[{ts}] {prefix} {msg}")
        if telegram:
            self.notifier.send(msg)
    
    def connect(self):
        """거래소 연결 - 포지션 확인 강화"""
        success, msg = self.exchange_mgr.connect()
        if not success:
            self.log(f"❌ {msg}", error=True, telegram=True)
            return False
        
        self.log(f"📊 레버리지 {LEVERAGE}배 설정 완료")
        
        # 🔍 거래소에서 포지션 확인
        existing = self.exchange_mgr.get_positions()
        
        if existing:
            self.position_mgr.load_from_exchange(existing)
        
        if existing:
            self.position_mgr.load_from_exchange(existing)
            self.log(f"💡 기존 포지션 발견! {existing['side']} {existing['size']:.4f} ETH @ ${existing['entry_price']:.2f}", telegram=True)
            self.log(f"   미실현 손익: ${existing.get('unrealized_pnl', 0):.2f}", telegram=False)
        else:
            self.log(f"✅ 포지션 없음 - 신규 진입 모드", telegram=False)
        
        # 잔고 확인
        balance = self.exchange_mgr.get_balance()
        self.log(f"💰 연결 성공! 잔고: ${balance['free']:.2f} (총 ${balance['total']:.2f})", telegram=True)
        
        # 📊 시작 시 거래 요약 보고 (텔레그램)
        self.send_report()
        
        # MarketDataProvider에 exchange 연결
        self.market_data.exchange = self.exchange_mgr.exchange
        
        return True
    
    def check_signals(self):
        """매매 신호 확인 및 실행 - 스위칭 지원 (보수적)"""
        # 데이터 조회
        df = self.market_data.fetch_data('5m', 100)
        if df is None:
            return
        
        market_state = self.market_data.get_current_market_state(df)
        if market_state is None:
            return
        
        current_price = market_state['price']
        mode = self.strategy.determine_mode(market_state)
        
        self.log(f"⏳ 분석 중... ETH ${current_price:.2f} | RSI {market_state['rsi']:.1f} | BB% {market_state['bb_pct']:.2f} | 추세 {market_state['trend']}")
        
        # ✅ 포지션 보유 중: SL/TP 체크만 수행 (스위칭 제거)
        if self.position_mgr.has_position():
            current_position = self.position_mgr.position
            entry_price = self.position_mgr.entry_price
            
            # 디버그 출력
            print(f"   [DEBUG] 포지션: {current_position}, 진입가: {entry_price}, 현재가: {current_price}")
            
            # 현재 PnL 계산
            direction = 1 if current_position == 'LONG' else -1
            if entry_price and entry_price > 0 and current_price and current_price > 0:
                current_pnl = ((current_price - entry_price) / entry_price) * 100 * direction
                print(f"   [DEBUG] PnL 계산: (({current_price} - {entry_price}) / {entry_price}) * 100 * {direction} = {current_pnl:.2f}%")
            else:
                current_pnl = 0
                print(f"   [DEBUG] PnL 계산 실패: entry_price={entry_price}, current_price={current_price}")
            
            self.log(f"   📍 보유 중 ({current_position}) | PnL: {current_pnl:+.2f}%", telegram=False)
            
            # SL/TP 체크만 수행
            self._check_exit()
            return
        
        # 주문 진행 중 체크
        if self.executor.pending_position:
            return
        
        # 🆕 청산 후 쿨다운 체크
        import time
        current_time = time.time()
        if current_time < self.exit_cooldown_until:
            remaining = int(self.exit_cooldown_until - current_time)
            mins = remaining // 60
            secs = remaining % 60
            self.log(f"   ⏳ 쿨다운 중... {mins}분 {secs}초 후 진입 가능 (이전: {self.last_exit_reason})", telegram=False)
            return
        
        # 🆕 시간대 필터 (밤/새벽 롱 진입 제한)
        from datetime import datetime
        current_hour = datetime.now().hour
        night_mode = 23 <= current_hour or current_hour < 7  # 23:00 ~ 07:00
        
        if night_mode:
            self.log(f"   🌙 야간 모드 (23:00-07:00): 롱 진입 제한, 숏 우선", telegram=False)
        
        # 롱 신호 확인
        long_ok, long_reason = self.strategy.check_long_signal(market_state, df)
        
        # 🎯 연속 신호 카운터 로직
        if long_ok:
            # 가격 변화 확인 (너무 많이 변했으면 카운터 리셋)
            if abs(current_price - self.last_signal_price) > self.max_signal_price_diff:
                self.long_signal_count = 0
                self.short_signal_count = 0
            
            self.long_signal_count += 1
            self.short_signal_count = 0  # 반대 신호 카운터 리셋
            self.last_signal_price = current_price
            
            self.log(f"   🟡 롱 신호 {self.long_signal_count}/{self.signal_confirmation} ({long_reason})", telegram=False)
            
            # 연속 신호 확인 완료!
            if self.long_signal_count >= self.signal_confirmation:
                # 🆕 다중 시간대 추세 정렬 확인
                multi_data = self.market_data.fetch_multi_timeframe_data(['3m', '5m', '15m'])
                is_aligned, alignment_msg = self.market_data.check_multi_timeframe_alignment(
                    multi_data, 'LONG'
                )
                
                if is_aligned:
                    # 🆕 야간 모드에서는 롱 진입 추가 제한
                    if night_mode and current_hour < 7:  # 새벽 00:00-07:00
                        self.log(f"   ⚠️ 야간 롱 진입 차단 (00:00-07:00): 관망", telegram=False)
                        return
                    
                    self.log(f"   ✅ 롱 신호 확인 완료! ({self.signal_confirmation}회 연속) | {alignment_msg}", telegram=True)
                    self.long_signal_count = 0  # 카운터 리셋
                    self._enter_long(current_price, mode, long_reason, market_state)
                    return
                else:
                    self.log(f"   ⏳ 롱 신호 있으나 추세 불일치: {alignment_msg}", telegram=False)
        else:
            # 롱 신호 없으면 롱 카운터 리셋
            if self.long_signal_count > 0:
                self.log(f"   ❌ 롱 신호 끊김 (카운터 리셋)", telegram=False)
            self.long_signal_count = 0
        
        # 숏 신호 확인 (롱이 없을 때만)
        if self.long_signal_count == 0:
            short_ok, short_reason = self.strategy.check_short_signal(market_state, df)
            
            if short_ok:
                # 가격 변화 확인
                if abs(current_price - self.last_signal_price) > self.max_signal_price_diff:
                    self.long_signal_count = 0
                    self.short_signal_count = 0
                
                self.short_signal_count += 1
                self.last_signal_price = current_price
                
                self.log(f"   🟡 숏 신호 {self.short_signal_count}/{self.signal_confirmation} ({short_reason})", telegram=False)
                
                # 연속 신호 확인 완료!
                if self.short_signal_count >= self.signal_confirmation:
                    # 🆕 다중 시간대 추세 정렬 확인
                    multi_data = self.market_data.fetch_multi_timeframe_data(['3m', '5m', '15m'])
                    is_aligned, alignment_msg = self.market_data.check_multi_timeframe_alignment(
                        multi_data, 'SHORT'
                    )
                    
                    if is_aligned:
                        self.log(f"   ✅ 숏 신호 확인 완료! ({self.signal_confirmation}회 연속) | {alignment_msg}", telegram=True)
                        self.short_signal_count = 0  # 카운터 리셋
                        self._enter_short(current_price, mode, short_reason, market_state)
                        return
                    else:
                        self.log(f"   ⏳ 숏 신호 있으나 추세 불일치: {alignment_msg}", telegram=False)
            else:
                # 숏 신호 없으면 숏 카운터 리셋
                if self.short_signal_count > 0:
                    self.log(f"   ❌ 숏 신호 끊김 (카운터 리셋)", telegram=False)
                self.short_signal_count = 0
        
        # 대기 메시지
        if self.long_signal_count == 0 and self.short_signal_count == 0:
            self.log(f"   ⏳ 신호 대기 중...", telegram=False)
    
    def _enter_long(self, price, mode, reason, market_state):
        """롱 진입 - 동적 SL 계산"""
        # 🆕 동적 SL 계산
        dynamic_sl = self.strategy.calculate_dynamic_sl_price(price, 'LONG', market_state, 0)
        _, tp, tp_pct = self.strategy.calculate_sl_tp(price, 'LONG', mode)
        
        self.log(f"\n🟢🟢 롱 진입! [{mode} MODE]", telegram=True)
        self.log(f"   가격: ${price:.2f}", telegram=False)
        self.log(f"   SL(동적): ${dynamic_sl:.2f}", telegram=False)
        self.log(f"   TP: ${tp:.2f}", telegram=False)
        self.log(f"   사유: {reason}", telegram=False)
        
        # 주문 실행
        success, result = self.executor.execute_long(price, dynamic_sl, tp, reason, mode)
        
        if success:
            self.position_mgr.open_position('LONG', price, result['amount'], mode, dynamic_sl, tp)
            self.notifier.send_signal('LONG', price, dynamic_sl, tp, f"{mode} - {reason}")
            self._record_entry('LONG', price, result['amount'], mode, market_state)
            # 🔄 동적 SL 추적 초기화
            self.strategy.peak_profit_tracker['LONG'] = 0
            # 신호 카운터 리셋
            self.long_signal_count = 0
            self.short_signal_count = 0
            # 📊 진입 시 거래 요약 보고
            self.send_report()
        else:
            self.log(f"   ❌ {result}", error=True, telegram=True)
    
    def _enter_short(self, price, mode, reason, market_state):
        """숏 진입 - 동적 SL 계산"""
        # 🆕 동적 SL 계산
        dynamic_sl = self.strategy.calculate_dynamic_sl_price(price, 'SHORT', market_state, 0)
        _, tp, tp_pct = self.strategy.calculate_sl_tp(price, 'SHORT', mode)
        
        self.log(f"\n🔴🔴 숏 진입! [{mode} MODE]", telegram=True)
        self.log(f"   가격: ${price:.2f}", telegram=False)
        self.log(f"   SL(동적): ${dynamic_sl:.2f}", telegram=False)
        self.log(f"   TP: ${tp:.2f}", telegram=False)
        self.log(f"   사유: {reason}", telegram=False)
        
        # 주문 실행
        success, result = self.executor.execute_short(price, dynamic_sl, tp, reason, mode)
        
        if success:
            self.position_mgr.open_position('SHORT', price, result['amount'], mode, dynamic_sl, tp)
            self.notifier.send_signal('SHORT', price, dynamic_sl, tp, f"{mode} - {reason}")
            self._record_entry('SHORT', price, result['amount'], mode, market_state)
            # 🔄 동적 SL 추적 초기화
            self.strategy.peak_profit_tracker['SHORT'] = 0
            # 신호 카운터 리셋
            self.long_signal_count = 0
            self.short_signal_count = 0
            # 📊 진입 시 거래 요약 보고
            self.send_report()
        else:
            self.log(f"   ❌ {result}", error=True, telegram=True)
    
    def _check_exit(self):
        """청산 체크 - 다중 시간대 분석 포함"""
        if not self.position_mgr.has_position():
            return
        
        # 🆕 다중 시간대 데이터 조회 (3m, 5m, 15m)
        multi_data = self.market_data.fetch_multi_timeframe_data(['3m', '5m', '15m'])
        
        # 현재 가격 (5분 기준)
        df_5m = multi_data.get('5m', {}).get('df')
        if df_5m is None:
            return
        
        current_price = df_5m['close'].iloc[-1]
        market_state_5m = self.market_data.get_current_market_state(df_5m)
        
        # 🆕 순차적 추세 반전 감지
        position = self.position_mgr.position
        sequential_reversal, reversal_reason = self.market_data.check_sequential_reversal(
            multi_data, position
        )
        
        # 현재 PnL 계산
        entry_price = self.position_mgr.entry_price
        direction = 1 if position == 'LONG' else -1
        pnl_pct = (current_price / entry_price - 1) * 100 * direction
        
        # 🆕 수익 중일 때 순차적 반전 감지 (0.3% 이상 수익)
        if pnl_pct >= 0.3 and sequential_reversal:
            self.log(f"\n⚠️ 순차적 추세 반전! {reversal_reason} | 수익: {pnl_pct:+.2f}%", telegram=True)
            self._execute_exit(current_price, f"SEQ ({reversal_reason})", pnl_pct)
            return
        
        # 🆕 동적 SL 계산 및 체크
        dynamic_sl_price = self.strategy.calculate_dynamic_sl_price(
            entry_price, position, market_state_5m, pnl_pct
        )
        
        if position == 'LONG' and current_price <= dynamic_sl_price:
            self.log(f"\n❌ 동적 손절! 현재 {pnl_pct:+.2f}% | SL가: ${dynamic_sl_price:.2f}", telegram=True)
            self._execute_exit(current_price, 'DSL (동적 손절)', pnl_pct)
            return
        if position == 'SHORT' and current_price >= dynamic_sl_price:
            self.log(f"\n❌ 동적 손절! 현재 {pnl_pct:+.2f}% | SL가: ${dynamic_sl_price:.2f}", telegram=True)
            self._execute_exit(current_price, 'DSL (동적 손절)', pnl_pct)
            return
        
        # 기존 SL/TP/TS 체크
        exit_type, pnl = self.strategy.should_exit(
            position, entry_price, current_price, market_state_5m
        )
        
        if exit_type:
            self._execute_exit(current_price, exit_type, pnl)
    
    def _execute_exit(self, price, reason, pnl):
        """청산 실행"""
        self.log(f"\n{'✅' if pnl > 0 else '❌'} 청산! {reason} | 수익률: {pnl:+.2f}%", telegram=True)
        
        position_data = {
            'side': self.position_mgr.position,
            'size': self.position_mgr.position_size
        }
        
        success, result = self.executor.close_position(position_data, price)
        
        if success:
            closed_position = self.position_mgr.position  # ⚠️ close 전에 저장!
            self.position_mgr.close_position(price, reason)
            self.notifier.send_exit(self.position_mgr.position, pnl, reason)
            # 🔄 드래그 스탑 추적 초기화
            self.strategy.reset_position_tracking(closed_position)
            
            # 🆕 청산 후 쿨다운 설정 (TS 청산 시 더 길게)
            import time
            self.last_exit_time = time.time()
            self.last_exit_reason = reason
            self.last_exit_pnl = pnl
            
            # TS 청산은 더 긴 쿨다운 (5분), 일반 청산은 3분
            cooldown_minutes = 5 if 'TS' in reason else 3
            self.exit_cooldown_until = self.last_exit_time + (cooldown_minutes * 60)
            
            self.log(f"   ⏳ 쿨다운 시작: {cooldown_minutes}분 동안 신규 진입 대기", telegram=True)
            self.log(f"      다음 진입 가능 시간: {datetime.fromtimestamp(self.exit_cooldown_until).strftime('%H:%M:%S')}", telegram=False)
            
            # 📊 청산 시 거래 요약 보고
            self.send_report()
        else:
            self.log(f"   ❌ 청산 실패: {result}", error=True, telegram=True)
    
    def _record_entry(self, side, price, size, mode, market_state):
        """진입 데이터 기록"""
        if not DATA_COLLECTION_ENABLED or not self.data_collector:
            return
        try:
            self.data_collector.record_trade({
                'trade_id': self.position_mgr.trade_count + 1,
                'type': side,
                'entry_price': price,
                'position_size': size,
                'mode': mode,
                'entry_rsi': market_state.get('rsi'),
                'entry_bb_pct': market_state.get('bb_pct'),
                'entry_trend': market_state.get('trend'),
                'entry_volume_ratio': market_state.get('volume_ratio'),
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            print(f"⚠️ 데이터 기록 실패: {e}")
    
    # _record_exit는 청산 시에 사용 (data_collector에 별도 메서드 없음)
    
    def send_report(self):
        """거래 요약 보고서 (시작/진입/청산 시에만)"""
        stats = self.position_mgr.get_stats()
        msg = f"📊 <b>LUMI 거래 요약</b>\n\n"
        msg += f"총 거래: {stats['total_trades']}"
        if stats['closed_trades'] > 0:
            msg += f"\n완료: {stats['closed_trades']}건"
            msg += f"\n승: {stats['wins']} / 패: {stats['losses']}"
            msg += f"\n승률: {stats['win_rate']:.1f}%"
            msg += f"\n총 수익: {stats['total_pnl_pct']:+.2f}%"
        
        # 현재 포지션 정보
        if self.position_mgr.has_position():
            current_pnl = self.position_mgr.get_current_pnl(0)  # 현장가 기준 PnL은 체크 시 계산
            msg += f"\n\n📍 현재 포지션: {self.position_mgr.position}"
            msg += f"\n진입가: ${self.position_mgr.entry_price:.2f}"
        
        self.notifier.send(msg)
    
    def run(self):
        """메인 루프"""
        self.log("🚀 LUMI HYBRID PRO v2.1 (모듈화) 시작", telegram=True)
        
        if not self.connect():
            return
        
        while self.running:
            try:
                # 신호 체크
                self.check_signals()
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                self.log("🛑 사용자 중단", telegram=True)
                break
            except Exception as e:
                self.log(f"❌ 오류: {e}", error=True, telegram=True)
                time.sleep(5)


def main():
    """메인 함수"""
    bot = TradingBot()
    bot.run()


if __name__ == "__main__":
    main()
