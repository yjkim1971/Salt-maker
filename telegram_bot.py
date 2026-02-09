"""
텔레그램 알림 모듈
- 관리자: 모든 로그 수신 (관리자 토큰)
- 관리자: 정의된 메시지는 시트 토큰으로도 수신
- 일반 사용자: 정의된 메시지만 시트 토큰으로 수신
"""

import telepot
import time
from utils import log

# config import는 함수 내에서 동적으로 처리


class TelegramBot:
    """텔레그램 봇 클래스 (관리자/사용자 분리)"""
    
    def __init__(self):
        """
        초기화
        - 관리자 봇과 사용자 봇을 분리하여 관리
        """
        # config를 여기서 import (순환 참조 방지)
        import config
        
        # [관리자용 봇] 모든 로그 수신
        self.is_admin = config.IS_ADMIN
        self.admin_token = config.ADMIN_TELEGRAM_TOKEN
        self.admin_chat_id = config.ADMIN_CHAT_ID
        self.admin_bot = None
        
        # 관리자 봇 초기화
        if self.is_admin and self.admin_token and self.admin_chat_id:
            try:
                self.admin_bot = telepot.Bot(self.admin_token)
                print(f"✅ 관리자 텔레그램 봇 초기화 완료")
            except Exception as e:
                print(f"⚠️ 관리자 봇 초기화 실패: {e}")
        
        # [사용자용 봇] 동적으로 설정됨 (시트별)
        self.user_token = None
        self.user_chat_id = None
        self.user_bot = None
        
        # 중복 메시지 방지
        self.last_message = ""
        self.last_message_time = 0
        self.duplicate_threshold = 3  # 3초
    
    def set_user_token(self, token, chat_id):
        """
        [사용자 토큰 설정] 시트별로 동적 설정
        
        Args:
            token: 시트 E27의 텔레그램 봇 토큰
            chat_id: 시트 E25의 채팅 ID
        """
        try:
            if token and chat_id:
                self.user_token = str(token).strip()
                self.user_chat_id = str(chat_id).strip()
                self.user_bot = telepot.Bot(self.user_token)
                print(f"✅ 사용자 봇 설정 완료 (Chat ID: {self.user_chat_id})")
                return True
            else:
                print(f"⚠️ 사용자 토큰/ID가 비어있습니다")
                return False
        except Exception as e:
            print(f"⚠️ 사용자 봇 설정 실패: {e}")
            return False
    
    def send_admin_log(self, message):
        """
        [관리자에게 로그 전송] 모든 로그 메시지
        
        Args:
            message: 로그 메시지
            
        Returns:
            bool: 성공 여부
        """
        if not self.is_admin or not self.admin_bot:
            return False
        
        try:
            current_time = time.time()
            
            # 중복 방지
            if message == self.last_message and (current_time - self.last_message_time) < self.duplicate_threshold:
                return True
            
            self.admin_bot.sendMessage(self.admin_chat_id, message)
            self.last_message = message
            self.last_message_time = current_time
            
            return True
        except Exception as e:
            print(f"⚠️ 관리자 로그 전송 실패: {e}")
            return False
    
    def send_user_message(self, message):
        """
        [사용자에게 정의된 메시지 전송]
        - 로그인 확인
        - 매매 완료
        - 티어 상황
        
        Args:
            message: 정의된 메시지
            
        Returns:
            bool: 성공 여부
        """
        if not self.user_bot or not self.user_chat_id:
            print(f"⚠️ 사용자 봇이 설정되지 않았습니다")
            return False
        
        try:
            self.user_bot.sendMessage(self.user_chat_id, message)
            return True
        except Exception as e:
            print(f"⚠️ 사용자 메시지 전송 실패: {e}")
            return False
    
    def send_message(self, message, message_type='log'):
        """
        [통합 메시지 전송 함수]
        
        Args:
            message: 전송할 메시지
            message_type: 'log' (모든 로그) 또는 'user' (정의된 메시지)
            
        Returns:
            bool: 성공 여부
        """
        success = False
        
        # [관리자일 때]
        if self.is_admin:
            if message_type == 'log':
                # 모든 로그 → 관리자 토큰으로
                success = self.send_admin_log(message)
            
            elif message_type == 'user':
                # 정의된 메시지 → 시트 토큰으로
                success = self.send_user_message(message)
        
        # [일반 사용자일 때]
        else:
            if message_type == 'user':
                # 정의된 메시지 → 시트 토큰으로만
                success = self.send_user_message(message)
            # message_type == 'log'일 때는 전송 안함
        
        return success
    
    def send_login_notification(self, user_id, success=True):
        """
        [정의된 메시지] 로그인 알림
        → 시트 토큰으로 전송
        """
        status = "✅ 로그인 성공" if success else "❌ 로그인 실패"
        message = f"{status}\n계정: {user_id}"
        return self.send_message(message, message_type='user')
    
    def send_order_notification(self, sheet_name, ticker, tier, stock_q, buy_p, buy_q, sell_p, sell_q, curr_p,
                                buy_status, sell_status, last_tier, buy_count, sell_count):
        """
        [정의된 메시지] 주문 알림
        → 시트 토큰으로 전송
        """
        try:
            line1 = f"{sheet_name} :${curr_p} {tier} / {last_tier} 티어"
            line2 = f" Buy ${buy_p} [{buy_count}]  / Sell ${sell_p} [{sell_count}] "
            msg = f"{line1}\n{line2}"
            
            return self.send_message(msg, message_type='user')
        
        except Exception as e:
            print(f"❌ 주문 알림 생성 오류: {e}")
            return False
    
    def send_tier_status(self, sheet_name, ticker, curr_tier, curr_price, buy_price, buy_qty, sell_price, sell_qty):
        """
        [정의된 메시지] 티어 상황 (감시 간격마다)
        → 시트 토큰으로 전송
        """
        message = (
            f"📊 [{sheet_name}] 현재 티어: {curr_tier}티어\n"
            f"   종목: {ticker}\n"
            f"   현재가: ${curr_price:.2f}\n"
            f"   매수: ${buy_price} x {buy_qty}주\n"
            f"   매도: ${sell_price} x {sell_qty}주"
        )
        return self.send_message(message, message_type='user')
    
    def send_error_notification(self, error_msg):
        """
        [정의된 메시지] 오류 알림
        → 시트 토큰으로 전송
        """
        message = f"⚠️ 오류 발생\n{error_msg}"
        return self.send_message(message, message_type='user')


# 전역 봇 인스턴스
telegram_bot = TelegramBot()


def send_telegram(message, message_type='log'):
    """
    간편 전송 함수
    
    Args:
        message: 전송할 메시지
        message_type: 'log' (모든 로그) 또는 'user' (정의된 메시지)
    """
    return telegram_bot.send_message(message, message_type)
