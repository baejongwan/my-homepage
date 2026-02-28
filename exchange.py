# -*- coding: utf-8 -*-
"""
modules/exchange.py - 거래소 연결 및 관리
"""

import ccxt
import os
from .utils import safe_float


class ExchangeManager:
    """Binance 거래소 연결 및 잔고/레버리지 관리"""
    
    def __init__(self, symbol="ETH/USDT", leverage=20):
        self.exchange = None
        self.symbol = symbol
        self.leverage = leverage
        self.is_connected = False
    
    def connect(self):
        """Binance 선물 거래소 연결"""
        try:
            # API 키 로드 (여러 환경변수 이름 지원)
            api_key = os.getenv('BINANCE_API_KEY', '') or os.getenv('API_KEY', '')
            secret = os.getenv('BINANCE_SECRET', '') or os.getenv('SECRET_KEY', '') or os.getenv('BINANCE_API_SECRET', '')
            
            if not api_key or not secret:
                return False, "API 키가 설정되지 않았습니다. .env 파일을 확인하세요."
            
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': secret,
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            self.exchange.set_sandbox_mode(False)
            
            # 레버리지 설정
            self._set_leverage()
            
            self.is_connected = True
            return True, "연결 성공"
            
        except Exception as e:
            self.is_connected = False
            return False, f"연결 실패: {e}"
    
    def _set_leverage(self):
        """레버리지 설정"""
        if not self.exchange:
            return
        try:
            self.exchange.fapiPrivatePostLeverage({
                'symbol': self.symbol.replace('/', ''),
                'leverage': self.leverage
            })
        except Exception as e:
            print(f"⚠️ 레버리지 설정 실패: {e}")
    
    def get_balance(self):
        """USDT 잔고 조회"""
        if not self.exchange:
            return {'free': 0, 'total': 0}
        try:
            balance = self.exchange.fetch_balance()
            return {
                'free': safe_float(balance.get('USDT', {}).get('free', 0)),
                'total': safe_float(balance.get('USDT', {}).get('total', 0))
            }
        except Exception as e:
            print(f"❌ 잔고 조회 실패: {e}")
            return {'free': 0, 'total': 0}
    
    def get_positions(self):
        """현재 포지션 조회"""
        if not self.exchange:
            return None
        try:
            # 방법 1: fetch_positions 사용
            positions = self.exchange.fetch_positions([self.symbol])
            
            # 심볼 형식 변환 (다양한 형식 지원)
            symbol_alternate = self.symbol.replace('/', '')  # ETH/USDT -> ETHUSDT
            symbol_ccxt_futures = f"{self.symbol}:USDT"      # ETH/USDT -> ETH/USDT:USDT (로그에서 확인된 형식)
            symbol_with_colon = self.symbol.replace('/', ':') # ETH/USDT -> ETH:USDT
            
            # Binance specific: 선물 심볼 형식
            binance_futures_symbol = symbol_alternate
            
            for pos in positions:
                pos_symbol = pos.get('symbol', '')
                contracts = safe_float(pos.get('contracts', 0)) or safe_float(pos.get('positionAmt', 0))
                
                # 각종 형식 비교 (ccxt 전용 형식 추가)
                if pos_symbol in [self.symbol, symbol_alternate, symbol_with_colon, binance_futures_symbol, symbol_ccxt_futures]:
                    if abs(contracts) > 0:
                        entry_price = safe_float(pos.get('entryPrice', 0)) or safe_float(pos.get('avgPrice', 0))
                        print(f"   ✅ 포지션 발견! {pos_symbol}: {contracts} @ ${entry_price}")
                        return {
                            'side': 'LONG' if contracts > 0 else 'SHORT',
                            'size': abs(contracts),
                            'entry_price': entry_price,
                            'unrealized_pnl': safe_float(pos.get('unrealizedPnl', 0)),
                            'notional': safe_float(pos.get('notional', 0)),
                            'leverage': safe_float(pos.get('leverage', 1))
                        }
            
            # 방법 2: balance에서 포지션 정보 확인 (Binance 스타일)
            try:
                balance = self.exchange.fetch_balance()
                positions_from_balance = balance.get('info', {}).get('positions', [])
                for pos in positions_from_balance:
                    pos_symbol = pos.get('symbol', '')
                    position_amt = safe_float(pos.get('positionAmt', 0))
                    if pos_symbol == symbol_alternate and abs(position_amt) > 0:
                        print(f"   ✅ balance에서 포지션 발견! {pos_symbol}: {position_amt}")
                        return {
                            'side': 'LONG' if position_amt > 0 else 'SHORT',
                            'size': abs(position_amt),
                            'entry_price': safe_float(pos.get('entryPrice', 0)),
                            'unrealized_pnl': safe_float(pos.get('unrealizedProfit', 0)),
                            'notional': abs(position_amt) * safe_float(pos.get('entryPrice', 0)),
                            'leverage': safe_float(pos.get('leverage', 1))
                        }
            except:
                pass
            
            print(f"   ⏳ 포지션 없음")
            return None
        except Exception as e:
            print(f"❌ 포지션 조회 실패: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_symbol_info(self):
        """거래 심볼 정보 조회"""
        if not self.exchange:
            return None
        try:
            markets = self.exchange.load_markets()
            return markets.get(self.symbol, {})
        except:
            return None
