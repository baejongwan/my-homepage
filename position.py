# -*- coding: utf-8 -*-
"""
modules/position.py - 포지션 상태 관리 (데이터 영속성 추가)
"""

from datetime import datetime
import json
import os
from pathlib import Path


class PositionManager:
    """포지션 상태 및 거래 기록 관리"""
    
    def __init__(self, history_file="logs/trade_history.json"):
        self.position = None  # 'LONG', 'SHORT', or None
        self.entry_price = None
        self.position_size = 0
        self.entry_time = None
        self.entry_mode = None
        self.sl_price = None
        self.tp_price = None
        self.trade_history = []
        self.trade_count = 0  # 거래 번호 카운터
        self.history_file = Path(history_file)
        
        # 영속된 거래 기록 로드
        self._load_history()
    
    def _load_history(self):
        """파일에서 거래 기록 로드"""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.trade_history = data.get('trade_history', [])
                    self.trade_count = data.get('trade_count', 0)
                    # 통계 계산
                    stats = self.get_stats()
                    print(f"📊 이전 거래 기록 로드 완료: 총 {stats['closed_trades']}건 거래, 승률 {stats['win_rate']:.1f}%")
        except Exception as e:
            print(f"⚠️ 거래 기록 로드 실패: {e}")
            self.trade_history = []
            self.trade_count = 0
    
    def _save_history(self):
        """거래 기록을 파일에 저장"""
        try:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'trade_history': self.trade_history,
                    'trade_count': self.trade_count,
                    'last_saved': datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 거래 기록 저장 실패: {e}")
    
    def open_position(self, side, price, size, mode='', sl=None, tp=None):
        """포지션 진입 기록"""
        self.position = side
        self.entry_price = price
        self.position_size = size
        self.entry_time = datetime.now()
        self.entry_mode = mode
        self.sl_price = sl
        self.tp_price = tp
        self.trade_count += 1  # 거래 카운트 증가
        
        record = {
            'type': 'entry',
            'side': side,
            'price': price,
            'size': size,
            'mode': mode,
            'sl': sl,
            'tp': tp,
            'time': self.entry_time.isoformat()
        }
        self.trade_history.append(record)
        return record
    
    def close_position(self, exit_price, reason=''):
        """포지션 청산 기록"""
        if not self.position or not self.entry_price:
            return None
        
        direction = 1 if self.position == 'LONG' else -1
        pnl_pct = (exit_price / self.entry_price - 1) * 100 * direction
        
        record = {
            'type': 'exit',
            'side': self.position,
            'entry_price': self.entry_price,
            'exit_price': exit_price,
            'size': self.position_size,
            'pnl_pct': pnl_pct,
            'mode': self.entry_mode,
            'reason': reason,
            'time': datetime.now().isoformat()
        }
        self.trade_history.append(record)
        
        # 💾 거래 기록 저장
        self._save_history()
        
        # 상태 리셋
        self._reset()
        
        return record
    
    def _reset(self):
        """포지션 상태 초기화"""
        self.position = None
        self.entry_price = None
        self.position_size = 0
        self.entry_time = None
        self.entry_mode = None
        self.sl_price = None
        self.tp_price = None
    
    def get_current_pnl(self, current_price):
        """현재 수익률 계산"""
        if not self.position or not self.entry_price:
            return 0
        
        direction = 1 if self.position == 'LONG' else -1
        return (current_price / self.entry_price - 1) * 100 * direction
    
    def has_position(self):
        """포지션 보유 여부"""
        return self.position is not None
    
    def load_from_exchange(self, exchange_position):
        """거래소에서 기존 포지션 로드"""
        if exchange_position:
            self.position = exchange_position['side']
            self.entry_price = exchange_position['entry_price']
            self.position_size = exchange_position['size']
            self.entry_time = datetime.now()
            return True
        return False
    
    def get_stats(self):
        """거래 통계"""
        entries = [t for t in self.trade_history if t['type'] == 'entry']
        exits = [t for t in self.trade_history if t['type'] == 'exit']
        
        wins = len([e for e in exits if e.get('pnl_pct', 0) > 0])
        losses = len([e for e in exits if e.get('pnl_pct', 0) <= 0])
        total_pnl = sum(e.get('pnl_pct', 0) for e in exits)
        
        return {
            'total_trades': len(entries),
            'closed_trades': len(exits),
            'wins': wins,
            'losses': losses,
            'win_rate': wins / len(exits) * 100 if exits else 0,
            'total_pnl_pct': total_pnl
        }
