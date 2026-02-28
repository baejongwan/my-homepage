# -*- coding: utf-8 -*-
"""
modules/executor.py - 주문 실행 모듈
"""

import time
from datetime import datetime


class OrderExecutor:
    """주문 실행 및 포지션 진입/청산"""
    
    def __init__(self, exchange_manager, config, notifier=None):
        self.exchange_mgr = exchange_manager
        self.config = config
        self.notifier = notifier
        self.pending_position = False
        self.last_entry_attempt = 0
        self.position_size = 0
    
    def calculate_position_size(self, price, balance_data):
        """포지션 크기 계산 (ALL-IN 모드)"""
        usdt_free = balance_data.get('free', 0)
        
        # 보수적 계산: 85%만 사용 + 1% 수수료
        margin_buffer = 0.15
        usable_margin = usdt_free * (1 - margin_buffer)
        fee_buffer = 0.01
        position_margin = usable_margin * (1 - fee_buffer)
        
        # 레버리지 적용
        leverage = self.config.get('LEVERAGE', 20)
        min_order = self.config.get('MIN_ORDER_SIZE_USDT', 25)
        
        notional_value = position_margin * leverage
        amount = notional_value / price if price > 0 else 0
        
        return {
            'margin': position_margin,
            'notional': notional_value,
            'amount': amount,
            'free_balance': usdt_free,
            'usable_margin': usable_margin,
            'is_valid': position_margin >= min_order
        }
    
    def execute_long(self, price, sl, tp, reason="", mode=""):
        """롱 포지션 진입"""
        if self.pending_position:
            return False, "이미 주문 진행 중"
        
        if time.time() - self.last_entry_attempt < 300:
            return False, "쿨다운 중 (5분)"
        
        if not self.exchange_mgr.exchange:
            return False, "거래소 연결 없음"
        
        self.pending_position = True
        symbol = self.config.get('SYMBOL', 'ETH/USDT')
        
        try:
            # 잔고 확인
            balance = self.exchange_mgr.get_balance()
            calc = self.calculate_position_size(price, balance)
            
            if not calc['is_valid']:
                min_order = self.config.get('MIN_ORDER_SIZE_USDT', 25)
                self.pending_position = False
                self.last_entry_attempt = time.time()
                return False, f"잔고 부족: ${calc['margin']:.2f} (최소 ${min_order})"
            
            # 디버깅 출력 (레버리지 계산 확인용)
            lev = self.config.get('LEVERAGE', 20)
            print(f"   💰 [실행기] 잔고 ${calc['free_balance']:.2f}")
            print(f"   💰 [실행기] 마진: ${calc['margin']:.2f} | 포지션: ${calc['notional']:.2f} | 레버리지: {lev}배")
            print(f"   💰 [실행기] ETH 수량: {calc['amount']:.4f}")
            
            # 주문 실행
            order = self.exchange_mgr.exchange.create_market_buy_order(
                symbol, calc['amount']
            )
            
            self.position_size = calc['amount']
            self.pending_position = False
            
            if self.notifier:
                self.notifier.send_order_filled(
                    "LONG", price, calc['amount'], calc['notional'], calc['margin']
                )
            
            return True, {
                'order_id': order.get('id'),
                'amount': calc['amount'],
                'notional': calc['notional'],
                'margin': calc['margin'],
                'price': price
            }
            
        except Exception as e:
            self.pending_position = False
            self.last_entry_attempt = time.time()
            return False, f"주문 실패: {e}"
    
    def execute_short(self, price, sl, tp, reason="", mode=""):
        """숏 포지션 진입"""
        if self.pending_position:
            return False, "이미 주문 진행 중"
        
        if time.time() - self.last_entry_attempt < 300:
            return False, "쿨다운 중 (5분)"
        
        if not self.exchange_mgr.exchange:
            return False, "거래소 연결 없음"
        
        self.pending_position = True
        symbol = self.config.get('SYMBOL', 'ETH/USDT')
        
        try:
            # 잔고 확인
            balance = self.exchange_mgr.get_balance()
            calc = self.calculate_position_size(price, balance)
            
            if not calc['is_valid']:
                min_order = self.config.get('MIN_ORDER_SIZE_USDT', 25)
                self.pending_position = False
                self.last_entry_attempt = time.time()
                return False, f"잔고 부족: ${calc['margin']:.2f} (최소 ${min_order})"
            
            # 주문 실행
            order = self.exchange_mgr.exchange.create_market_sell_order(
                symbol, calc['amount']
            )
            
            self.position_size = calc['amount']
            self.pending_position = False
            
            if self.notifier:
                self.notifier.send_order_filled(
                    "SHORT", price, calc['amount'], calc['notional'], calc['margin']
                )
            
            return True, {
                'order_id': order.get('id'),
                'amount': calc['amount'],
                'notional': calc['notional'],
                'margin': calc['margin'],
                'price': price
            }
            
        except Exception as e:
            self.pending_position = False
            self.last_entry_attempt = time.time()
            return False, f"주문 실패: {e}"
    
    def close_position(self, position, current_price):
        """포지션 청산"""
        if not self.exchange_mgr.exchange:
            return False, "거래소 연결 없음"
        
        symbol = self.config.get('SYMBOL', 'ETH/USDT')
        close_amount = position.get('size', 0)
        
        if close_amount <= 0:
            return False, "청산할 포지션 없음"
        
        try:
            if position['side'] == 'LONG':
                order = self.exchange_mgr.exchange.create_market_sell_order(
                    symbol, close_amount
                )
            else:
                order = self.exchange_mgr.exchange.create_market_buy_order(
                    symbol, close_amount
                )
            
            return True, {'order_id': order.get('id'), 'amount': close_amount}
            
        except Exception as e:
            return False, f"청산 실패: {e}"
