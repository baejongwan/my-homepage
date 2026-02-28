# -*- coding: utf-8 -*-
"""
modules/utils.py - 유틸리티 함수
"""


def safe_float(value):
    """None-safe float 변환"""
    if value is None:
        return 0.0
    try:
        return float(value)
    except:
        return 0.0


def safe_int(value):
    """None-safe int 변환"""
    if value is None:
        return 0
    try:
        return int(value)
    except:
        return 0
