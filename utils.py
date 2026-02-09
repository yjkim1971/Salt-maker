"""
유틸리티 함수 모음
RSI 계산, 시장 시간 체크, 해상도 관리, 로그 저장 등
"""

import os
import json
from datetime import datetime
import win32con
from win32api import EnumDisplaySettings, ChangeDisplaySettings
from win32con import ENUM_CURRENT_SETTINGS

# 설정값 로드
try:
    from config import MARKET_TIMES, RESOLUTION_WIDTH, RESOLUTION_HEIGHT, USER_NAME, GRID_CONFIG_PATH
except ImportError:
    MARKET_TIMES = {"PRE": ["18:00", "23:30"], "REGULAR": ["23:30", "06:00"], "AFTER": ["06:00", "10:00"]}
    RESOLUTION_WIDTH, RESOLUTION_HEIGHT = 1280, 720
    USER_NAME = "사용자"
    GRID_CONFIG_PATH = "task.json"


def get_first_user_name():
    """task.json의 첫 번째 자동 로그인 항목에서 사용자 이름을 추출"""
    if not os.path.exists(GRID_CONFIG_PATH):
        return "사용자"

    try:
        with open(GRID_CONFIG_PATH, 'r', encoding='utf-8') as f:
            tasks = json.load(f)

        task_list = list(tasks.values()) if isinstance(tasks, dict) else tasks

        for task in task_list:
            if task.get('type') == "자동 로그인":
                details = task.get('details', "")
                items = [i.strip() for i in details.split(' / ')]  # 🔥 구분자 통일
                if items:
                    return items[0]

        return "사용자"
    except Exception as e:
        print(f"❌ 사용자 이름 추출 오류: {e}")
        return "사용자"


def calculate_rsi(prices, period=14):
    """순수 파이썬 RSI 계산 (Wilder's Smoothing)"""
    if not prices or len(prices) <= period:
        return 50.0

    deltas = [prices[i + 1] - prices[i] for i in range(len(prices) - 1)]
    up = [d if d > 0 else 0 for d in deltas]
    down = [-d if d < 0 else 0 for d in deltas]

    avg_gain = sum(up[:period]) / period
    avg_loss = sum(down[:period]) / period

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + up[i]) / period
        avg_loss = (avg_loss * (period - 1) + down[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def get_market_session():
    """현재 미국 시장 세션 반환"""
    now = datetime.now()
    current_time = now.strftime("%H:%M")

    if MARKET_TIMES["PRE"][0] <= current_time < MARKET_TIMES["PRE"][1]:
        return "PRE"
    elif current_time >= MARKET_TIMES["REGULAR"][0] or current_time < MARKET_TIMES["REGULAR"][1]:
        return "REGULAR"
    elif MARKET_TIMES["AFTER"][0] <= current_time < MARKET_TIMES["AFTER"][1]:
        return "AFTER"
    else:
        return "CLOSED"


class DisplayManager:
    """디스플레이 해상도 관리 클래스"""

    def __init__(self):
        try:
            self.original_settings = EnumDisplaySettings(None, ENUM_CURRENT_SETTINGS)
            print(f"   >> 원래 해상도 저장: {self.original_settings.PelsWidth}x{self.original_settings.PelsHeight}")
        except:
            self.original_settings = None

    def change_resolution(self, width=None, height=None):
        width = width or RESOLUTION_WIDTH
        height = height or RESOLUTION_HEIGHT

        try:
            devmode = EnumDisplaySettings(None, ENUM_CURRENT_SETTINGS)
            devmode.PelsWidth = width
            devmode.PelsHeight = height
            devmode.Fields = win32con.DM_PELSWIDTH | win32con.DM_PELSHEIGHT
            ChangeDisplaySettings(devmode, 0)
            log(f"🖥️ 해상도 변경 완료: {width}x{height}", "✅")
        except Exception as e:
            print(f"   ⚠️ 해상도 변경 실패: {e}")

    def restore_resolution(self):
        if not self.original_settings: return
        try:
            ChangeDisplaySettings(self.original_settings, 0)
            log("🖥️ 해상도 복구 완료", "✅")
        except Exception as e:
            print(f"   >> 해상도 복구 오류: {e}")


def get_current_time():
    return datetime.now().strftime('%H:%M:%S')


def log(message, symbol="ℹ️", send_telegram=None):
    """
    화면 출력, 파일 저장 및 선택적 텔레그램 전송
    
    Args:
        message: 로그 메시지
        symbol: 이모지 심볼
        send_telegram: True(강제전송)/False(전송안함)/None(자동판단)
    """
    now = datetime.now()
    time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{time_str}] {symbol} {message}"

    # 1. 콘솔 출력
    print(log_entry)

    # 2. 파일 저장
    try:
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_path = os.path.join(log_dir, f"log_{now.strftime('%Y-%m-%d')}.txt")
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")
    except Exception as e:
        print(f"❌ 로그 파일 저장 실패: {e}")

    # 3. 텔레그램 전송 (중요한 로그만)
    if send_telegram is None:
        # 자동 판단: 중요한 심볼만 텔레그램 전송
        important_symbols = [
            "🔥",   # 주문 실행
            "✅",   # 성공
            "❌",   # 실패
            "🚨",   # 치명적 오류
            "⚠️",   # 경고
            "💰",   # 체결 🔥 추가
            "🔔",   # 체결 감지 🔥 추가
            "🎯",   # 티어 매칭
            "🔒",   # 자동 차단
            "🔑",   # 로그인
            "🛑",   # 중단
            "📢",   # 중요 알림
            "⏳"    # 미체결
        ]
        send_telegram = symbol in important_symbols
    
    # 텔레그램 전송
    if send_telegram:
        try:
            # 순환 import 방지를 위해 함수 내부에서 import
            from telegram_bot import telegram_bot
            # 시간 정보 없이 간결하게 전송
            telegram_bot.send_message(f"{symbol} {message}")
        except Exception as e:
            # 텔레그램 전송 실패해도 프로그램은 계속 실행
            print(f"⚠️ 텔레그램 전송 실패: {e}")


def safe_int(value, default=0):
    try:
        if isinstance(value, str):
            value = value.replace(',', '').strip()
        return int(float(value))
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    try:
        if isinstance(value, str):
            value = value.replace(',', '').strip()
        return float(value)
    except (ValueError, TypeError):
        return default
