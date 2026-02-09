"""
Salt Maker - 그리드 매매 전략
"""

from .base_strategy import BaseTradingStrategy


class GridTradingStrategy(BaseTradingStrategy):
    """
    그리드 매매 전략
    
    시트: "시트1" 고정
    매수 신호: buy_check=TRUE AND (현재가 < 평단가 OR 평단가==0)
    매도 신호: sell_check=TRUE AND 현재가 >= 평단가*1.1 AND 보유수량>0
    """
    
    def __init__(self, schedule):
        super().__init__(schedule)
        
        # 그리드 매매 전용 변수
        self.total_seed = 0
        self.tier_division = 0
        self.one_buy_amount = 0
        self.buy_check = False
        self.sell_check = False
        self.tier_update = False
        self.avg_price = 0.0
        self.holding_qty = 0
    
    def load_config(self):
        """그리드 매매 설정 로드"""
        # "시트1" 워크시트 선택
        self.worksheet = self.sheet.worksheet("시트1")
        print(f"📄 워크시트 연결: 시트1")
        
        # 설정값 로드
        try:
            self.total_seed = float(self.get_cell_value('E10') or 0)
            self.tier_division = int(self.get_cell_value('E12') or 40)
            self.one_buy_amount = float(self.get_cell_value('E14') or 0)
            
            # 체크박스 (TRUE/FALSE 문자열)
            self.buy_check = self.get_cell_value('E17').upper() == 'TRUE'
            self.sell_check = self.get_cell_value('E18').upper() == 'TRUE'
            self.tier_update = self.get_cell_value('E16').upper() == 'TRUE'
            
            # 평단가 (Y2 셀)
            self.avg_price = float(self.get_cell_value('Y2') or 0)
            
            # 보유수량 (K11 셀)
            self.holding_qty = int(self.get_cell_value('K11') or 0)
            
            print(f"\n📊 그리드 매매 설정")
            print(f"   총 시드: {self.total_seed:,.0f}원")
            print(f"   티어 분할: {self.tier_division}회")
            print(f"   1회 매수금: {self.one_buy_amount:,.0f}원")
            print(f"   평단가: {self.avg_price:,.2f}원")
            print(f"   보유수량: {self.holding_qty}주")
            print(f"   매수체크: {self.buy_check}")
            print(f"   매도체크: {self.sell_check}")
            
        except Exception as e:
            print(f"❌ 설정 로드 오류: {e}")
            raise
    
    def check_buy_signal(self):
        """
        매수 신호 체크
        
        조건: buy_check=TRUE AND (현재가 < 평단가 OR 평단가==0)
        """
        if not self.buy_check:
            return False
        
        current_price = self.get_current_price()
        
        if current_price == 0:
            return False
        
        # 평단가가 0이거나 현재가가 평단가보다 낮으면 매수
        if self.avg_price == 0 or current_price < self.avg_price:
            print(f"🔔 매수 신호 발생!")
            print(f"   현재가: {current_price:,.2f}원")
            print(f"   평단가: {self.avg_price:,.2f}원")
            return True
        
        return False
    
    def check_sell_signal(self):
        """
        매도 신호 체크
        
        조건: sell_check=TRUE AND 현재가 >= 평단가*1.1 AND 보유수량>0
        """
        if not self.sell_check:
            return False
        
        if self.holding_qty == 0:
            return False
        
        current_price = self.get_current_price()
        target_price = self.avg_price * 1.1
        
        if current_price >= target_price:
            print(f"🔔 매도 신호 발생!")
            print(f"   현재가: {current_price:,.2f}원")
            print(f"   목표가: {target_price:,.2f}원 (평단가 +10%)")
            return True
        
        return False
    
    def execute_buy(self):
        """매수 실행"""
        current_price = self.get_current_price()
        
        # 매수 수량 계산 (1회 매수금 / 현재가)
        buy_qty = int(self.one_buy_amount / current_price)
        
        if buy_qty == 0:
            print("⚠️  매수 수량이 0입니다.")
            return
        
        print(f"\n💰 매수 실행")
        print(f"   종목: {self.ticker}")
        print(f"   가격: {current_price:,.2f}원")
        print(f"   수량: {buy_qty}주")
        print(f"   금액: {current_price * buy_qty:,.0f}원")
        
        # TODO: HTS API 실제 매수 주문
        
        # 평단가 재계산
        new_avg_price = self.calculate_avg_price(
            self.avg_price,
            self.holding_qty,
            current_price,
            buy_qty
        )
        
        # 보유수량 업데이트
        new_holding_qty = self.holding_qty + buy_qty
        
        # 구글 시트 업데이트
        self.update_cell_value('Y2', new_avg_price)
        self.update_cell_value('K11', new_holding_qty)
        
        # 로컬 변수 업데이트
        self.avg_price = new_avg_price
        self.holding_qty = new_holding_qty
        
        print(f"✅ 매수 완료")
        print(f"   새 평단가: {new_avg_price:,.2f}원")
        print(f"   총 보유: {new_holding_qty}주")
        
        # 거래 이력 기록
        self.log_trade_history("매수", current_price, buy_qty, f"평단가: {new_avg_price:,.2f}")
        
        # 텔레그램 알림
        msg = f"🟢 {self.ticker} 매수\n{current_price:,.2f}원 × {buy_qty}주\n평단가: {new_avg_price:,.2f}원"
        self.send_telegram_message(msg)
    
    def execute_sell(self):
        """매도 실행 (전량 매도)"""
        current_price = self.get_current_price()
        sell_qty = self.holding_qty
        
        print(f"\n💵 매도 실행")
        print(f"   종목: {self.ticker}")
        print(f"   가격: {current_price:,.2f}원")
        print(f"   수량: {sell_qty}주")
        print(f"   금액: {current_price * sell_qty:,.0f}원")
        
        # 수익률 계산
        profit_rate = ((current_price - self.avg_price) / self.avg_price) * 100
        profit_amount = (current_price - self.avg_price) * sell_qty
        
        print(f"   평단가: {self.avg_price:,.2f}원")
        print(f"   수익률: {profit_rate:,.2f}%")
        print(f"   수익금: {profit_amount:,.0f}원")
        
        # TODO: HTS API 실제 매도 주문
        
        # 구글 시트 초기화
        self.update_cell_value('Y2', 0)
        self.update_cell_value('K11', 0)
        
        # 로컬 변수 초기화
        self.avg_price = 0
        self.holding_qty = 0
        
        print(f"✅ 매도 완료")
        
        # 거래 이력 기록
        self.log_trade_history("매도", current_price, sell_qty, f"수익률: {profit_rate:,.2f}%")
        
        # 텔레그램 알림
        msg = f"🔴 {self.ticker} 매도\n{current_price:,.2f}원 × {sell_qty}주\n수익률: {profit_rate:,.2f}%\n수익금: {profit_amount:,.0f}원"
        self.send_telegram_message(msg)
