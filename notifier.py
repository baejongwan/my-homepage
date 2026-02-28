# -*- coding: utf-8 -*-
"""
modules/notifier.py - 텔레그램 알림 모듈
"""

import requests


class TelegramNotifier:
    """텔레그램 알림 관리"""
    
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.enabled = bool(token and chat_id)
    
    def send(self, message):
        """기본 메시지 전송"""
        if not self.enabled:
            return
        try:
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            payload = {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
            requests.post(url, json=payload, timeout=5)
        except:
            pass
    
    def send_signal(self, action, price, sl, tp, reason=""):
        """진입 신호 알림"""
        emoji = "🟢" if action == "LONG" else "🔴"
        msg = f"{emoji} <b>진입 신호!</b>\n\n"
        msg += f"방향: {action}\n"
        msg += f"가격: ${price:.2f}\n"
        msg += f"SL: ${sl:.2f}\n"
        msg += f"TP: ${tp:.2f}\n"
        if reason:
            msg += f"\n사유: {reason}"
        self.send(msg)
    
    def send_exit(self, action, pnl, reason):
        """청산 알림"""
        emoji = "✅" if pnl > 0 else "❌"
        msg = f"{emoji} <b>청산!</b>\n\n"
        msg += f"방향: {action}\n"
        msg += f"수익률: {pnl:+.2f}%\n"
        msg += f"사유: {reason}"
        self.send(msg)
    
    def send_order_filled(self, action, price, amount, notional_value, margin):
        """주문 체결 알림"""
        emoji = "✅" if action == "LONG" else "🔴"
        msg = f"{emoji} <b>주문 체결</b>\n\n"
        msg += f"방향: {action}\n"
        msg += f"가격: ${price:.2f}\n"
        msg += f"수량: {amount:.4f} ETH\n"
        msg += f"포지션: ${notional_value:.2f}\n"
        msg += f"마진: ${margin:.2f}"
        self.send(msg)
    
    def send_error(self, error):
        """오류 알림"""
        self.send(f"⚠️ <b>오류:</b>\n{error}")
