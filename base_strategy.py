"""
Salt Maker - 베이스 전략 클래스
모든 매매 전략의 공통 기능을 제공합니다.
"""

from abc import ABC, abstractmethod
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import json


class BaseTradingStrategy(ABC):
    """
    모든 매매 전략의 베이스 클래스
    
    공통 기능:
    - 구글 시트 연결
    - 셀 읽기/쓰기
    - 현재가 조회
    - 평단가 계산
    - 텔레그램 알림
    - 거래 이력 기록
    """
    
    def __init__(self, schedule):
        """
        Args:
            schedule: {
                'sheet_id': '0801',
                'ticker': 'PLUG',
                'start_time': '09:00:00',
                'end_time': '07:59:00',
                'interval': 60
            }
        """
        self.schedule = schedule
        self.sheet_id = schedule['sheet_id']
        self.ticker = schedule['ticker']
        self.start_time = schedule['start_time']
        self.end_time = schedule['end_time']
        self.interval = schedule['interval']
        
        # 구글 시트 연결
        self.sheet = None
        self.worksheet = None
        
        print(f"📌 전략 초기화: {self.ticker} ({self.sheet_id})")
    
    def _connect_to_sheet(self):
        """구글 시트 연결"""
        try:
            # settings.json에서 스프레드시트 ID 로드
            with open('settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            spreadsheet_id = settings.get('spreadsheet_id', '')
            
            if not spreadsheet_id:
                raise ValueError("settings.json에 spreadsheet_id가 없습니다.")
            
            # 구글 시트 인증
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_name(
                'credentials.json', 
                scope
            )
            
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(spreadsheet_id)
            
            print(f"✅ 구글 시트 연결 성공: {spreadsheet_id}")
            
        except Exception as e:
            print(f"❌ 구글 시트 연결 실패: {e}")
            raise
    
    def get_cell_value(self, cell):
        """셀 값 읽기"""
        if not self.worksheet:
            raise ValueError("워크시트가 연결되지 않았습니다.")
        
        try:
            value = self.worksheet.acell(cell).value
            return value if value else ""
        except Exception as e:
            print(f"❌ 셀 읽기 오류 ({cell}): {e}")
            return ""
    
    def update_cell_value(self, cell, value):
        """셀 값 쓰기"""
        if not self.worksheet:
            raise ValueError("워크시트가 연결되지 않았습니다.")
        
        try:
            self.worksheet.update_acell(cell, value)
            print(f"✅ 셀 업데이트: {cell} = {value}")
        except Exception as e:
            print(f"❌ 셀 쓰기 오류 ({cell}): {e}")
    
    def get_current_price(self):
        """현재가 조회 (K9 셀)"""
        try:
            price_str = self.get_cell_value('K9')
            return float(price_str) if price_str else 0.0
        except ValueError:
            print(f"⚠️  현재가 변환 오류: {price_str}")
            return 0.0
    
    def calculate_avg_price(self, current_avg, current_qty, buy_price, buy_qty):
        """
        평단가 계산
        
        평단가 = (기존평단가 × 기존수량 + 매수가 × 매수수량) / (기존수량 + 매수수량)
        """
        if current_qty + buy_qty == 0:
            return 0.0
        
        total_cost = (current_avg * current_qty) + (buy_price * buy_qty)
        total_qty = current_qty + buy_qty
        
        return total_cost / total_qty
    
    def send_telegram_message(self, message):
        """텔레그램 알림 전송"""
        try:
            # settings.json에서 봇 토큰 로드
            with open('settings.json', 'r', encoding='utf-8') as f:
                settings = json.load(f)
            
            bot_token = settings.get('telegram_bot_token', '')
            chat_id = settings.get('telegram_chat_id', '')
            
            if not bot_token or not chat_id:
                print("⚠️  텔레그램 설정이 없습니다.")
                return
            
            # TODO: 텔레그램 API 호출
            print(f"📱 텔레그램 알림: {message}")
            
        except Exception as e:
            print(f"❌ 텔레그램 전송 오류: {e}")
    
    def log_trade_history(self, action, price, quantity, note=""):
        """거래 이력 기록"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {action} | {self.ticker} | {price}원 × {quantity}주 | {note}"
        print(f"📝 {log_message}")
        
        # TODO: 거래 이력 시트에 기록
    
    # =========================================================================
    # 추상 메서드 (각 전략에서 구현 필수)
    # =========================================================================
    
    @abstractmethod
    def load_config(self):
        """전략별 설정 로드"""
        pass
    
    @abstractmethod
    def check_buy_signal(self):
        """매수 신호 체크"""
        pass
    
    @abstractmethod
    def check_sell_signal(self):
        """매도 신호 체크"""
        pass
    
    @abstractmethod
    def execute_buy(self):
        """매수 실행"""
        pass
    
    @abstractmethod
    def execute_sell(self):
        """매도 실행"""
        pass
    
    def run(self):
        """메인 실행 루프"""
        print(f"\n{'='*60}")
        print(f"🚀 {self.__class__.__name__} 시작: {self.ticker}")
        print(f"{'='*60}")
        
        # 구글 시트 연결
        self._connect_to_sheet()
        
        # 설정 로드
        self.load_config()
        
        print(f"\n⏰ 매매 시간: {self.start_time} ~ {self.end_time}")
        print(f"🔄 체크 주기: {self.interval}초\n")
        
        try:
            while True:
                # 매수 신호 체크
                if self.check_buy_signal():
                    self.execute_buy()
                
                # 매도 신호 체크
                if self.check_sell_signal():
                    self.execute_sell()
                
                # 대기
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print(f"\n⏹️  {self.ticker} 전략 종료")
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")
            import traceback
            traceback.print_exc()
