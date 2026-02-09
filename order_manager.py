"""
주문 관리 모듈 v2.0
최종 통합 체크 시스템 적용
"""

import time
from datetime import datetime
import re
import pyautogui
import pyperclip
from pywinauto import mouse

import config
from config import (
    COORDS_BUY_TAB, COORDS_BUY_TYPE, COORDS_BUY_ORDER_TYPE, COORDS_BUY_LIMIT,
    COORDS_BUY_QUANTITY, COORDS_BUY_PRICE, COORDS_BUY_BUTTON, COORDS_BUY_CONFIRM,
    COORDS_SELL_TAB, COORDS_SELL_TYPE, COORDS_SELL_ORDER_TYPE, COORDS_SELL_LIMIT,
    COORDS_SELL_QUANTITY, COORDS_SELL_PRICE, COORDS_SELL_BUTTON, COORDS_SELL_CONFIRM,
    COORDS_UNFILLED_TAB, COORDS_UNFILLED_COUNTRY, COORDS_UNFILLED_USA,
    COORDS_UNFILLED_TICKER, COORDS_UNFILLED_SELECT, COORDS_UNFILLED_INPUT,
    COORDS_UNFILLED_SEARCH, COORDS_UNFILLED_COUNT,
    WAIT_TIME
)
from utils import log


def click_point(coords, wait=None):
    """좌표 클릭 헬퍼 함수"""
    wait = wait or WAIT_TIME["MEDIUM"]
    mouse.click(button='left', coords=coords)
    time.sleep(wait)


class OrderManager:
    """주문 관리 클래스 (최종 통합 체크 시스템)"""

    def _clean_val(self, val, is_price=True):
        """주문 가격/수량 정제용 함수"""
        import re
        try:
            clean_s = re.sub(r'[^0-9.]', '', str(val))
            if not clean_s:
                return "0.00" if is_price else "0"

            if is_price:
                return "{:.2f}".format(float(clean_s))
            else:
                return str(int(float(clean_s)))
        except:
            return "0.00" if is_price else "0"

    def __init__(self, hts_controller, telegram_manager=None):
        self.hts = hts_controller
        self.telegram_manager = telegram_manager

    def cancel_unfilled_order(self, ticker, unfilled_price):
        """미체결 주문 취소"""
        try:
            log(f"🗑️ 미체결 주문 취소 시작: {ticker} @ {unfilled_price}", "🔄")
            click_point(COORDS_UNFILLED_TAB)
            time.sleep(WAIT_TIME["MEDIUM"])
            unfilled_row_coord = (460, 442)
            mouse.double_click(coords=unfilled_row_coord)
            time.sleep(WAIT_TIME["MEDIUM"])
            cancel_button_coord = (600, 500)
            mouse.click(coords=cancel_button_coord)
            time.sleep(WAIT_TIME["MEDIUM"])
            confirm_coord = (640, 400)
            mouse.click(coords=confirm_coord)
            time.sleep(WAIT_TIME["LONG"])
            log(f"✅ 미체결 주문 취소 완료: {ticker}", "✅")
            return True
        except Exception as e:
            log(f"❌ 미체결 취소 실패: {e}", "❌")
            return False

    def check_unfilled_orders(self, ticker):
        """미체결 주문 확인"""
        try:
            log(f"미체결 확인 시작: {ticker}", "🔍")
            click_point(COORDS_UNFILLED_TAB)
            click_point(COORDS_UNFILLED_COUNTRY)
            click_point(COORDS_UNFILLED_USA)
            click_point(COORDS_UNFILLED_TICKER)
            click_point(COORDS_UNFILLED_SELECT)
            click_point(COORDS_UNFILLED_INPUT)
            self.hts.main_dlg.type_keys('^a{BACKSPACE}')
            self.hts.main_dlg.type_keys(ticker + "{ENTER}", with_spaces=True)
            click_point(COORDS_UNFILLED_SEARCH)
            time.sleep(1.0)
            mouse.double_click(coords=COORDS_UNFILLED_COUNT)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(WAIT_TIME["MEDIUM"])
            unfilled_count_raw = pyperclip.paste().strip()
            is_unfilled_exists = False
            unfilled_num = 0
            if unfilled_count_raw.isdigit():
                unfilled_num = int(unfilled_count_raw)
                if unfilled_num > 0:
                    is_unfilled_exists = True
            result = {
                'exists': is_unfilled_exists,
                'count': unfilled_num,
                'data': unfilled_count_raw
            }
            if is_unfilled_exists:
                log(f"미체결 존재: {unfilled_num}주", "⏳")
            else:
                log("미체결 없음", "✅")
            return result
        except Exception as e:
            log(f"미체결 확인 오류: {e}", "❌")
            return {'exists': False, 'count': 0, 'data': ''}

    def final_trade_check(self, trade_type, ticker, curr_price, avg_price,
                          buy_p, buy_q, sell_p, sell_q, 
                          sheet_buy_stop, sheet_sell_stop,
                          curr_tier, last_tier):
        """
        🔥 최종 주문 전 모든 조건 통합 체크
        
        Args:
            trade_type: "BUY" 또는 "SELL"
            ticker: 종목 코드
            curr_price: 현재가
            avg_price: 평단가
            buy_p: 매수가
            buy_q: 매수량
            sell_p: 매도가
            sell_q: 매도량
            sheet_buy_stop: E18 (매수금지)
            sheet_sell_stop: E20 (매도금지)
            curr_tier: 현재 티어
            last_tier: 마지막 티어
            
        Returns:
            tuple: (bool: 주문 가능 여부, str: 사유)
        """
        log(f"\n{'='*60}", "")
        log(f"🔍 [{trade_type}] 최종 매매 조건 통합 검증", "🎯")
        log(f"{'='*60}", "")
        
        # 매수 최종 체크
        if trade_type == "BUY":
            log(f"📊 매수 조건 검증 시작", "🔍")
            log(f"  ├─ 종목: {ticker}", "")
            log(f"  ├─ 현재가: ${curr_price}", "")
            log(f"  ├─ 평단가: ${avg_price}", "")
            log(f"  ├─ 매수가: ${buy_p}", "")
            log(f"  ├─ 매수량: {buy_q}주", "")
            log(f"  ├─ 현재 티어: {curr_tier}", "")
            log(f"  └─ 마지막 티어: {last_tier}", "")
            
            # 조건 1: 매수금지 체크 (E18)
            log(f"\n  [조건 1] 매수금지(E18) 체크", "")
            if sheet_buy_stop:
                log(f"  └─ ❌ 거부: E18 = TRUE (시트에서 매수 차단됨)", "🛑")
                return False, "🛑 매수금지(E18=TRUE)"
            log(f"  └─ ✅ 통과: E18 = FALSE", "")
            
            # 조건 2: 마지막 티어 체크
            log(f"\n  [조건 2] 마지막 티어 체크", "")
            if str(curr_tier) == str(last_tier):
                log(f"  └─ ❌ 거부: 현재 티어({curr_tier}) = 마지막 티어({last_tier})", "🛑")
                return False, f"🛑 마지막티어({last_tier})"
            log(f"  └─ ✅ 통과: {curr_tier} ≠ {last_tier}", "")
            
            # 조건 3: 평단가 체크
            log(f"\n  [조건 3] 평단가 비교", "")
            if curr_price >= avg_price:
                log(f"  └─ ❌ 거부: 현재가(${curr_price}) >= 평단가(${avg_price})", "🛑")
                return False, f"⏸️ 현재가({curr_price})>=평단가"
            log(f"  └─ ✅ 통과: ${curr_price} < ${avg_price}", "")
            
            # 조건 4: 가격 차이 체크 (10% 이내)
            log(f"\n  [조건 4] 가격 차이 검증 (기준: 10%)", "")
            price_diff = abs(float(buy_p) - float(curr_price)) / float(curr_price) * 100
            log(f"  ├─ 매수가: ${buy_p}", "")
            log(f"  ├─ 현재가: ${curr_price}", "")
            log(f"  └─ 차이: {price_diff:.2f}%", "")
            
            if price_diff > 10 and float(buy_p) > float(curr_price):
                log(f"  └─ ❌ 거부: 가격 차이({price_diff:.2f}%) > 10% (비정상)", "🛑")
                return False, f"🛑 가격차이과다({price_diff:.1f}%)"
            log(f"  └─ ✅ 통과: 정상 범위", "")
            
            # 조건 5: 매수량 체크
            log(f"\n  [조건 5] 매수량 검증", "")
            if buy_q <= 0:
                log(f"  └─ ❌ 거부: 매수량({buy_q}주) ≤ 0", "🛑")
                return False, f"🛑 매수량없음({buy_q}주)"
            log(f"  └─ ✅ 통과: {buy_q}주 > 0", "")
            
            # 최종 승인
            log(f"\n{'='*60}", "")
            log(f"✅ 매수 최종 승인!", "🎉")
            log(f"  └─ 모든 조건 통과 → 매수 주문 실행", "")
            log(f"{'='*60}\n", "")
            return True, "✅ 매수조건충족"
        
        # 매도 최종 체크
        elif trade_type == "SELL":
            log(f"📊 매도 조건 검증 시작", "🔍")
            log(f"  ├─ 종목: {ticker}", "")
            log(f"  ├─ 현재가: ${curr_price}", "")
            log(f"  ├─ 평단가: ${avg_price}", "")
            log(f"  ├─ 매도가: ${sell_p}", "")
            log(f"  └─ 매도량: {sell_q}주", "")
            
            # 조건 1: 매도금지 체크 (E20)
            log(f"\n  [조건 1] 매도금지(E20) 체크", "")
            if sheet_sell_stop:
                log(f"  └─ ❌ 거부: E20 = TRUE (시트에서 매도 차단됨)", "🛑")
                return False, "🛑 매도금지(E20=TRUE)"
            log(f"  └─ ✅ 통과: E20 = FALSE", "")
            
            # 조건 2: 평단가 체크
            log(f"\n  [조건 2] 평단가 비교", "")
            if curr_price <= avg_price:
                log(f"  └─ ❌ 거부: 현재가(${curr_price}) <= 평단가(${avg_price})", "🛑")
                return False, f"⏸️ 현재가({curr_price})<=평단가"
            log(f"  └─ ✅ 통과: ${curr_price} > ${avg_price}", "")
            
            # 조건 3: 가격 차이 체크 (10% 이내)
            log(f"\n  [조건 3] 가격 차이 검증 (기준: 10%)", "")
            price_diff = abs(float(sell_p) - float(curr_price)) / float(curr_price) * 100
            log(f"  ├─ 매도가: ${sell_p}", "")
            log(f"  ├─ 현재가: ${curr_price}", "")
            log(f"  └─ 차이: {price_diff:.2f}%", "")
            
            if price_diff > 10 and float(sell_p) < float(curr_price):
                log(f"  └─ ❌ 거부: 가격 차이({price_diff:.2f}%) > 10% (비정상)", "🛑")
                return False, f"🛑 가격차이과다({price_diff:.1f}%)"
            log(f"  └─ ✅ 통과: 정상 범위", "")
            
            # 조건 4: 매도량 체크
            log(f"\n  [조건 4] 매도량 검증", "")
            if sell_q <= 0:
                log(f"  └─ ❌ 거부: 매도량({sell_q}주) ≤ 0", "🛑")
                return False, f"🛑 매도량없음({sell_q}주)"
            log(f"  └─ ✅ 통과: {sell_q}주 > 0", "")
            
            # 최종 승인
            log(f"\n{'='*60}", "")
            log(f"✅ 매도 최종 승인!", "🎉")
            log(f"  └─ 모든 조건 통과 → 매도 주문 실행", "")
            log(f"{'='*60}\n", "")
            return True, "✅ 매도조건충족"
        
        # 알 수 없는 거래 유형
        log(f"❌ 알 수 없는 거래 유형: {trade_type}", "⚠️")
        return False, "❌ 알수없는거래유형"

    def place_buy_order(self, ticker, buy_price, buy_quantity, market_session="REGULAR"):
        """매수 주문 실행"""
        try:
            log(f"🛒 매수 주문 실행: {ticker} {buy_price}달러 {buy_quantity}주", "🔥")
            click_point(COORDS_BUY_TAB)
            click_point(COORDS_BUY_TYPE)
            click_point(COORDS_BUY_ORDER_TYPE)
            now = datetime.now()
            market_open = now.replace(hour=9, minute=0, second=0, microsecond=0)
            market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
            if market_open <= now <= market_close:
                log("장중 지정가 선택", "▶")
                click_point(COORDS_BUY_LIMIT)
            else:
                log("시간외 지정가 선택", "⚠️")
                click_point(COORDS_BUY_LIMIT)
            q_val = self._clean_val(buy_quantity, is_price=False)
            click_point(COORDS_BUY_QUANTITY)
            self.hts.main_dlg.type_keys('^a{BACKSPACE}')
            self.hts.main_dlg.type_keys(str(buy_quantity), with_spaces=True)
            p_val = self._clean_val(buy_price, is_price=True)
            click_point(COORDS_BUY_PRICE)
            self.hts.main_dlg.type_keys('^a{BACKSPACE}')
            self.hts.main_dlg.type_keys(str(buy_price), with_spaces=True)
            click_point(COORDS_BUY_BUTTON)
            time.sleep(0.5)
            time.sleep(0.8)
            click_point((640, 405))
            log(f"예수금 부족 확인 좌표(640, 405) 클릭 시도", "🖱️")
            time.sleep(0.5)
            unfilled_check = self.check_unfilled_orders(ticker)
            if not unfilled_check.get('exists', False):
                log(f"⚠️ {ticker}: 미체결 데이터 없음 - 예수금 부족 판단", "❌")
                return "LACK_OF_MONEY"
            log(f"✅ 매수 주문 완료: {ticker} {buy_price}달러", "✅")
            return True
        except Exception as e:
            log(f"❌ 매수 주문 실행 중 오류: {e}", "❌")
            return False

    def place_sell_order(self, ticker, sell_price, sell_quantity, market_session="REGULAR"):
        """매도 주문 실행"""
        try:
            log(f"✨ 매도 주문 실행: {ticker} {sell_price}달러 {sell_quantity}주", "🔥")
            click_point(COORDS_SELL_TAB)
            click_point(COORDS_SELL_TYPE)
            click_point(COORDS_SELL_ORDER_TYPE)
            now = datetime.now()
            market_open = now.replace(hour=23, minute=0, second=0, microsecond=0)
            market_close = now.replace(hour=4, minute=30, second=0, microsecond=0)
            if market_open <= now <= market_close:
                log("장중 지정가 선택", "▶")
                click_point(COORDS_SELL_LIMIT)
            else:
                log("시간외 지정가 선택", "⚠️")
                click_point(COORDS_SELL_LIMIT)
            q_val = self._clean_val(sell_quantity, is_price=False)
            click_point(COORDS_SELL_QUANTITY)
            self.hts.main_dlg.type_keys('^a{BACKSPACE}')
            self.hts.main_dlg.type_keys(str(sell_quantity), with_spaces=True)
            p_val = self._clean_val(sell_price, is_price=True)
            click_point(COORDS_SELL_PRICE)
            self.hts.main_dlg.type_keys('^a{BACKSPACE}')
            self.hts.main_dlg.type_keys(str(sell_price), with_spaces=True)
            click_point(COORDS_SELL_BUTTON)
            time.sleep(0.5)
            log(f"✅ 매도 주문 완료: {ticker} {sell_price}달러 / {sell_quantity}주", "✅")
            return True
        except Exception as e:
            log(f"❌ 매도 주문 오류: {e}", "❌")
            return False

    def execute_trade_logic(self, sheet_data, ticker, hts_stock_q, sheet_stock_q,
                            buy_p, buy_q, sell_p, sell_q, buy_chk, sell_chk,
                            ws, last_tier, curr_tier, sheet_buy_stop, sheet_sell_stop,
                            curr_price, buy_count, sell_count, avg_price):
        """
        매매 로직 실행 (최종 통합 체크 적용)
        """
        result = {
            'buy_status': 'STAY',
            'sell_status': 'STAY',
            'buy_executed': False,
            'sell_executed': False
        }

        try:
            # 1. 미체결 확인
            import pyperclip
            pyperclip.copy("")
            time.sleep(0.3)
            unfilled = self.check_unfilled_orders(ticker)
            unfilled_data = str(unfilled['data']).replace(",", "").strip()

            # 미체결이 있으면 가격 비교
            if unfilled['exists']:
                try:
                    unfilled_price = float(unfilled_data)
                    is_same_buy = abs(unfilled_price - float(buy_p)) < 0.01
                    is_same_sell = abs(unfilled_price - float(sell_p)) < 0.01
                    
                    if is_same_buy or is_same_sell:
                        log(f"⏳ 미체결 대기 중: {unfilled_price} (현재 매수: {buy_p}, 매도: {sell_p})", "⏳")
                        if is_same_buy:
                            result['buy_status'] = f"⏳ 매수대기({unfilled_data})"
                        elif is_same_sell:
                            result['sell_status'] = f"⏳ 매도대기({unfilled_data})"
                        return result
                    else:
                        log(f"🔄 미체결 가격 불일치 감지!", "⚠️")
                        log(f"   미체결 가격: {unfilled_price}", "⚠️")
                        log(f"   현재 매수가: {buy_p} / 매도가: {sell_p}", "⚠️")
                        log(f"   → 미체결 주문 취소 후 재주문 진행", "🔄")
                        
                        if self.cancel_unfilled_order(ticker, unfilled_price):
                            log(f"✅ 미체결 취소 완료. 재주문 진행", "✅")
                        else:
                            log(f"❌ 미체결 취소 실패. 이번 사이클 Skip", "❌")
                            result['buy_status'] = "미체결취소실패"
                            result['sell_status'] = "미체결취소실패"
                            return result
                        
                except Exception as e:
                    log(f"⚠️ 미체결 가격 비교 중 오류: {e}", "⚠️")
                    return result

            # 2. 미체결 없음 - 매매 판단 시작
            log("✅ 미체결 없음 - 매매 판단 시작", "🚀")
            log(f"🎯 평단가: ${avg_price:.2f} / 현재가: ${curr_price}", "🔍")
            
            # 🔥 매수 최종 체크 및 실행
            trade_can_buy = False
            buy_check_reason = ""
            
            if not buy_chk:
                # 최종 통합 체크
                trade_can_buy, buy_check_reason = self.final_trade_check(
                    "BUY", ticker, curr_price, avg_price,
                    buy_p, buy_q, sell_p, sell_q,
                    sheet_buy_stop, sheet_sell_stop,
                    curr_tier, last_tier
                )
                
                if trade_can_buy:
                    # 모든 조건 통과 → 주문 실행
                    log(f"🎯 매수 주문 실행 결정: {buy_check_reason}", "🔥")
                    order_res = self.place_buy_order(ticker, buy_p, buy_q)
                    
                    if order_res == "LACK_OF_MONEY":
                        result['buy_status'] = "LACK_OF_MONEY_POPUP"
                        # 예수금 부족 시 E18 자동 활성화
                        try:
                            ws.update_acell('E18', True)
                            log(f"🔒 {ticker}: 예수금 부족 → E18 자동 활성화", "🔒")
                        except Exception as e:
                            log(f"⚠️ E18 업데이트 실패: {e}", "⚠️")
                    elif order_res:
                        result['buy_status'] = f"✅ 매수완료({buy_p})"
                        result['buy_executed'] = True
                    else:
                        result['buy_status'] = "❌ 매수실패"
                else:
                    # 조건 미충족 → 주문 불가
                    log(f"🛑 매수 불가: {buy_check_reason}", "🛑")
                    result['buy_status'] = buy_check_reason
                    
                    # 가격 차이 과다 시 E18 자동 활성화
                    if "가격차이과다" in buy_check_reason:
                        try:
                            ws.update_acell('E18', True)
                            log(f"🔒 {ticker}: 가격 차이 과다 → E18 자동 활성화", "🔒")
                        except Exception as e:
                            log(f"⚠️ E18 업데이트 실패: {e}", "⚠️")
            else:
                result['buy_status'] = "🔴 매수금지(시트)"

            # 🔥 매도 최종 체크 및 실행
            trade_can_sell = False
            sell_check_reason = ""
            
            if not sell_chk:
                # 최종 통합 체크
                trade_can_sell, sell_check_reason = self.final_trade_check(
                    "SELL", ticker, curr_price, avg_price,
                    buy_p, buy_q, sell_p, sell_q,
                    sheet_buy_stop, sheet_sell_stop,
                    curr_tier, last_tier
                )
                
                if trade_can_sell:
                    # 모든 조건 통과 → 주문 실행
                    log(f"🎯 매도 주문 실행 결정: {sell_check_reason}", "🔥")
                    order_res = self.place_sell_order(ticker, sell_p, sell_q)
                    
                    if order_res:
                        result['sell_status'] = f"✅ 매도완료({sell_p})"
                        result['sell_executed'] = True
                    else:
                        result['sell_status'] = "❌ 매도실패"
                else:
                    # 조건 미충족 → 주문 불가
                    log(f"🛑 매도 불가: {sell_check_reason}", "🛑")
                    result['sell_status'] = sell_check_reason
                    
                    # 가격 차이 과다 시 E20 자동 활성화
                    if "가격차이과다" in sell_check_reason:
                        try:
                            ws.update_acell('E20', True)
                            log(f"🔒 {ticker}: 가격 차이 과다 → E20 자동 활성화", "🔒")
                        except Exception as e:
                            log(f"⚠️ E20 업데이트 실패: {e}", "⚠️")
            else:
                result['sell_status'] = "🔵 매도금지(시트)"

            return result

        except Exception as e:
            log(f"❌ 매매 로직 실행 오류: {e}", "❌")
            return result
