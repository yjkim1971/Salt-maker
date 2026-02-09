"""
트레이딩 봇 설정 파일
모든 상수와 설정값을 한 곳에서 관리
"""

import os
import settings_manager

# ==========================================
# 사용자 정보
# ==========================================
USER_NAME = ""
INVESTMENT_MODE = "REAL"

# ==========================================
# 관리자 모드 설정 (텔레그램 봇용)
# ==========================================
IS_ADMIN = False  # True로 설정 시 모든 로그 수신
ADMIN_TELEGRAM_TOKEN = ""  # 관리자 전용 봇 토큰
ADMIN_CHAT_ID = ""  # 관리자 챗 ID

# ==========================================
# 파일 경로
# ==========================================
GRID_CONFIG_PATH = "tasks.json"

# ==========================================
# Google Sheets & Telegram 설정
# ==========================================
# 기본값 (영진님의 기존 데이터)
DEFAULT_SERVICE_ACCOUNT_FILE = 'credentials.json'
DEFAULT_SPREADSHEET_ID = "13u35m4s5a9PCIq2RyxY0oEAPd30_mqJZR16ZWoed6J0"
DEFAULT_TELEGRAM_TOKEN = "6346103042:AAFlQyY8kSlka6L1-3hXyp0JGHUywOQcua0"
DEFAULT_CHAT_ID = "6263291866"

# settings.json에서 설정 로드 시도
_settings = settings_manager.load_settings()

# settings.json에 값이 있으면 사용, 없으면 기본값 사용
#SERVICE_ACCOUNT_FILE = _settings['google_sheets'].get('credentials_file') or DEFAULT_SERVICE_ACCOUNT_FILE
#SPREADSHEET_ID = _settings['google_sheets'].get('spreadsheet_id') or DEFAULT_SPREADSHEET_ID
#TELEGRAM_TOKEN = _settings['telegram'].get('bot_token') or DEFAULT_TELEGRAM_TOKEN
#CHAT_ID = _settings['telegram'].get('chat_id') or DEFAULT_CHAT_ID


#--------------- 위에 주석 처리는 동적 구조로 갖고 오도록 코딩 ..  main.py 만  실행 할때는 아래 코드 사용
# 1. 파일 경로 설정 (현재 파일과 동일한 폴더의 credentials.json)
current_dir = os.path.dirname(os.path.abspath(__file__))
SERVICE_ACCOUNT_FILE = os.path.join(current_dir, "credentials.json")

# 2. 기존 에러 발생 구문 수정
# _settings['google_sheets']를 직접 참조하지 않고 파일 존재 여부로 체크합니다.
if os.path.exists(SERVICE_ACCOUNT_FILE):
    # 파일이 존재하면 이 경로를 사용하도록 로직 고정
    print(f"✅ 구글 인증 파일 로드 완료: {SERVICE_ACCOUNT_FILE}")
else:
    # 파일이 없을 경우에 대비한 기본값 또는 예외 처리
    DEFAULT_SERVICE_ACCOUNT_FILE = os.path.join(current_dir, "credentials.json")
    SERVICE_ACCOUNT_FILE = DEFAULT_SERVICE_ACCOUNT_FILE
    print(f"⚠️ 경고: 동일 폴더 내에 credentials.json 파일이 없습니다.")


# 1. google_sheets 섹션을 안전하게 가져옵니다.
# google_sheets_settings = _settings.get('google_sheets', {})  <-- 이 줄은 주석 처리하거나 지우셔도 됩니다.

# 여기에 실제 복사한 시트 ID를 붙여넣으세요 (반드시 따옴표 안에!)
SPREADSHEET_ID = "13u35m4s5a9PCIq2RyxY0oEAPd30_mqJZR16ZWoed6J0"

print(f"✅ 시트 ID 설정 완료: {SPREADSHEET_ID[:10]}...")

# 만약 시트 ID가 반드시 필요하다면 아래와 같이 직접 입력하셔도 됩니다.
# SPREADSHEET_ID = "여기에_실제_구글_시트_ID를_넣으세요"

print(f"✅ 시트 ID 로드 완료: {SPREADSHEET_ID[:10]}...")


#-------------------------------------------------------------------------------------



# ==========================================
# RSI 매매 전략 설정
# ==========================================
RSI_LOW_LIMIT = 35    # 매수 기준
RSI_HIGH_LIMIT = 60   # 매도 기준
RSI_CHK = "FALSE"     # RSI 사용 여부

# ==========================================
# 구글 시트 데이터 인덱스 (열 위치)
# ==========================================
# 시트의 각 행(row)은 리스트로 로드되며, 인덱스는 0부터 시작
# A=0, B=1, C=2, ..., Z=25, AA=26, AB=27, AC=28

IDX_TIER_NAME = 14        # O열 - 티어 번호
IDX_BUY_PRICE = 25        # Z열 - 매수가
IDX_BUY_QUANTITY = 26     # AA열 - 매수 수량
IDX_SELL_PRICE = 27       # AB열 - 매도가
IDX_SELL_QUANTITY = 28    # AC열 - 매도 수량

# ==========================================
# HTS 화면 좌표 설정 (1280x720 해상도 기준)
# ==========================================

COORDS_CLEAR = (932, 628)

# 주문 종류 선택
COORDS_ORDER_TYPE_LIST = (397, 187)
COORDS_LIMIT_PRE = (640, 320)      # 프리마켓 지정가
COORDS_LIMIT_REG = (423, 205)      # 정규장 지정가
COORDS_LIMIT_AFTER = (640, 450)    # 애프터마켓 지정가

# 2220 화면 좌표
COORDS_TICKER_INPUT = (20, 119)    # 종목 입력 필드
COORDS_ACCOUNT_LIST = (397, 121)   # 계좌 리스트

# 🔥 계좌 선택 좌표 (1~9번)
COORDS_ACCOUNT_1 = (397, 143)
COORDS_ACCOUNT_2 = (397, 163)
COORDS_ACCOUNT_3 = (397, 183)
COORDS_ACCOUNT_4 = (397, 203)
COORDS_ACCOUNT_5 = (397, 223)
COORDS_ACCOUNT_6 = (397, 243)
COORDS_ACCOUNT_7 = (397, 263)
COORDS_ACCOUNT_8 = (397, 228)      # 기존 값 유지
COORDS_ACCOUNT_9 = (397, 303)

# 현재가 확인
COORDS_PRICE_TAB = (386, 149)
COORDS_TICKER1_INPUT = (414, 176)  # 매수, 매도 시에 동일한 좌표 사용
COORDS_AUTO_PRICE = (406, 280)
COORDS_PRICE_FIELD = (439, 257)

# 잔고 확인
COORDS_QUANTITY_TAB = (444, 150)
COORDS_AUTO_100 = (405, 236)
COORDS_QUANTITY_FIELD = (437, 216)

# 매수 주문
COORDS_BUY_TAB = (386, 149)
COORDS_BUY_TYPE = (415, 172)
COORDS_BUY_ORDER_TYPE = (495, 196)
COORDS_BUY_LIMIT = (423, 212)
COORDS_BUY_QUANTITY = (441, 216)
COORDS_BUY_PRICE = (442, 259)
COORDS_BUY_BUTTON = (391, 343)
COORDS_BUY_CONFIRM = (601, 372)

# 매도 주문
COORDS_SELL_TAB = (443, 148)
COORDS_SELL_TYPE = (413, 173)
COORDS_SELL_ORDER_TYPE = (492, 194)
COORDS_SELL_LIMIT = (423, 205)
COORDS_SELL_QUANTITY = (437, 216)
COORDS_SELL_PRICE = (442, 300)
COORDS_SELL_BUTTON = (397, 342)
COORDS_SELL_CONFIRM = (600, 383)

# 미체결 확인
COORDS_UNFILLED_TAB = (399, 394)
COORDS_UNFILLED_COUNTRY = (433, 396)
COORDS_UNFILLED_USA = (378, 427)
COORDS_UNFILLED_TICKER = (470, 396)
COORDS_UNFILLED_SELECT = (460, 427)
COORDS_UNFILLED_INPUT = (544, 396)
COORDS_UNFILLED_SEARCH = (744, 396)
COORDS_UNFILLED_COUNT = (734, 442)

# ==========================================
# 시장 시간 설정 (한국 시간 기준)
# ==========================================
MARKET_TIMES = {
    "PRE": ("18:00", "23:30"),      # 프리마켓
    "REGULAR": ("23:30", "06:00"),   # 정규장
    "AFTER": ("06:00", "10:00"),     # 애프터마켓
    "CLOSED": ("10:00", "18:00")     # 장외시간
}

# ==========================================
# 해상도 설정
# ==========================================
RESOLUTION_WIDTH = 1280
RESOLUTION_HEIGHT = 720

# ==========================================
# 대기 시간 설정 (초)
# ==========================================
WAIT_TIME = {
    "SHORT": 0.3,
    "MEDIUM": 0.5,
    "LONG": 1.0,
    "LOGIN": 15,
    "CERT": 30,
    "SCREEN_LOAD": 5
}
