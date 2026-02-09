"""
구글 시트 데이터 관리 모듈
시트 연결, 데이터 읽기/쓰기 담당
"""

import gspread
from google.oauth2.service_account import Credentials
from config import SERVICE_ACCOUNT_FILE, SPREADSHEET_ID
from utils import log, safe_int, safe_float


class GoogleSheetManager:
    """구글 시트 관리 클래스"""

    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.connect()

    def connect(self):
        """구글 시트 연결"""
        try:
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
            creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scopes)
            self.client = gspread.authorize(creds)
            self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
            log("구글 시트 연결 성공", "✅")

        except Exception as e:
            log(f"구글 시트 연결 실패: {e}", "❌")
            raise

    def get_worksheet(self, sheet_name):
        """워크시트 가져오기"""
        try:
            return self.spreadsheet.worksheet(sheet_name)
        except Exception as e:
            log(f"시트 '{sheet_name}' 로드 실패: {e}", "⚠️")
            return None

    def load_trading_data(self, sheet_name):
        """
        매매용 데이터 로드

        Returns:
            dict: 매매에 필요한 모든 데이터
        """
        try:
            ws = self.get_worksheet(sheet_name)
            if not ws:
                return None

            log(f"시트({sheet_name}) 데이터 로딩 중...", "📡")

            # 전체 데이터 한 번에 로드 (속도 향상)
            sheet_data = ws.get('A1:AC30')

            def get_val(r, c):
                """안전한 셀 값 가져오기"""
                try:
                    return sheet_data[r - 1][c - 1]
                except (IndexError, TypeError):
                    return ""

            # 기본 정보 추출
            data = {
                'ticker': get_val(8, 5),  # E8
                'acc_no': get_val(6, 5),  # E6
                'acc_cnt': get_val(7, 5),  # E7
                'curr_tier': get_val(12, 11),  # K12
                'last_tier': get_val(12, 5),  # E12
                'sheet_stock_q': get_val(10, 11),  # K10 - 🔥 이전 HTS 잔고
                'avg_price': get_val(8, 11),  # K8 - 평단가
                'sell_chk': get_val(18, 5),  # E18
                'buy_chk': get_val(20, 5),  # E20
                'worksheet': ws,
                'sheet_data': sheet_data
            }

            # 불린 변환
            data['sell_chk'] = str(data['sell_chk']).upper() == "TRUE"
            data['buy_chk'] = str(data['buy_chk']).upper() == "TRUE"

            # 숫자 데이터 정제
            import re
            def clean_to_float(val):
                if not val: return 0.0
                val_str = str(val).strip()
                clean_val = re.sub(r'[^0-9.]', '', val_str)
                return safe_float(clean_val)

            data['avg_price'] = clean_to_float(data['avg_price'])
            data['sheet_stock_q'] = safe_int(re.sub(r'[^0-9]', '', str(data['sheet_stock_q'])))

            # 매수/매도 가격 및 수량 초기화
            data['buy_p'] = 0.0
            data['buy_q'] = 0
            data['sell_p'] = 0.0
            data['sell_q'] = 0

            log(f"데이터 로딩 완료: {data['ticker']} / 티어:{data['curr_tier']}", "✅")

            return data

        except Exception as e:
            log(f"데이터 로딩 오류: {e}", "❌")
            return None

    def find_tier_by_price(self, sheet_data, current_price):
        """
        현재가를 기준으로 티어 결정
        
        Args:
            sheet_data: 시트 데이터
            current_price: 현재가
            
        Returns:
            dict: {
                'curr_tier': 티어명,
                'buy_p': 매수가,
                'buy_q': 매수량,
                'sell_p': 매도가,
                'sell_q': 매도량,
                'mid_price': 중간가,
                'sheet_stock_q': 시트 목표 잔고
            }
        """
        try:
            best_match = None
            min_diff = float('inf')
            matched_row = None
            
            # 1. 현재가와 가장 가까운 평단가를 가진 티어 찾기
            for i in range(5, len(sheet_data)):
                try:
                    avg_price = safe_float(self.clean_float(sheet_data[i][24]))  # Y열 (평단가)
                    
                    if avg_price == 0:
                        continue
                    
                    # 평단가와 현재가 차이
                    diff = abs(current_price - avg_price)
                    
                    if diff < min_diff:
                        min_diff = diff
                        best_match = avg_price
                        matched_row = i
                        
                except (ValueError, IndexError):
                    continue
            
            if matched_row is None:
                log(f"❌ 티어 매칭 실패: 현재가 ${current_price}", "⚠️")
                return None
            
            # 2. 티어 데이터 추출
            import re
            tier_name = str(sheet_data[matched_row][21])  # V열 (티어명)
            avg_price = safe_float(self.clean_float(sheet_data[matched_row][24]))  # Y열 (평단가)
            buy_p = safe_float(self.clean_float(sheet_data[matched_row][25]))
            buy_q = safe_int(re.sub(r'[^0-9]', '', str(sheet_data[matched_row][26])))
            sell_p = safe_float(self.clean_float(sheet_data[matched_row][27]))
            sell_q = safe_int(re.sub(r'[^0-9]', '', str(sheet_data[matched_row][28])))
            sheet_stock_q = safe_int(sheet_data[matched_row][22])  # W열 (목표 잔고)
            
            log(f"🎯 가격 기준 매칭: {tier_name}티어 (평단가:${avg_price:.2f} / 현재가:${current_price:.2f})", "✅")
            log(f"   📊 매수: ${buy_p} ({buy_q}주) / 매도: ${sell_p} ({sell_q}주)", "🔍")
            
            tier_data = {
                'matched_row': matched_row + 1,
                'curr_tier': tier_name,
                'avg_price': avg_price,  # 평단가 추가
                'buy_p': buy_p,
                'buy_q': buy_q,
                'sell_p': sell_p,
                'sell_q': sell_q,
                'sheet_stock_q': sheet_stock_q
            }
            
            return tier_data
            
        except Exception as e:
            log(f"가격 기준 티어 검색 오류: {e}", "❌")
            import traceback
            traceback.print_exc()
            return None
    
    def clean_float(self, val):
        """숫자 정제"""
        if not val: 
            return 0.0
        import re
        clean_val = re.sub(r'[^0-9.]', '', str(val))
        return safe_float(clean_val)

    def find_tier_by_quantity(self, sheet_data, hts_stock_q):
        """
        범위 매칭 방식으로 HTS 잔고에 가장 가까운 티어 찾기 + 차이 계산

        Args:
            sheet_data: 시트 전체 데이터
            hts_stock_q: HTS에서 가져온 실제 보유 수량

        Returns:
            dict: {
                'curr_tier': 티어명,
                'sheet_stock_q': 시트 잔고,
                'buy_p': 매수가,
                'buy_q': 원래 매수량,
                'sell_p': 매도가,
                'sell_q': 원래 매도량,
                'stock_diff': 잔고 차이 (HTS - 시트),
                'adjusted_buy_q': 보정된 매수량,
                'adjusted_sell_q': 보정된 매도량
            }
        """
        try:
            best_match = None
            min_diff = float('inf')
            matched_row = None
            
            # 1. 가장 가까운 티어 찾기 (범위 매칭)
            for i in range(5, len(sheet_data)):
                try:
                    sheet_stock_q = safe_int(sheet_data[i][22])  # W열 (잔고량)
                    diff = abs(hts_stock_q - sheet_stock_q)
                    
                    if diff < min_diff:
                        min_diff = diff
                        best_match = sheet_stock_q
                        matched_row = i
                        
                        # 정확히 일치하면 즉시 종료
                        if diff == 0:
                            log(f"✅ 정확 매칭: {hts_stock_q}주", "🎯")
                            break
                            
                except (ValueError, IndexError):
                    continue
            
            if matched_row is None:
                log(f"❌ 티어 매칭 실패: HTS 잔고 {hts_stock_q}주", "⚠️")
                return None
            
            # 2. 숫자 정제 함수
            import re
            def clean_float(val):
                if not val: return 0.0
                clean_val = re.sub(r'[^0-9.]', '', str(val))
                return safe_float(clean_val)
            
            # 3. 티어 데이터 추출
            tier_name = str(sheet_data[matched_row][21])  # V열 (티어명)
            original_buy_q = safe_int(re.sub(r'[^0-9]', '', str(sheet_data[matched_row][26])))  # AA열
            original_sell_q = safe_int(re.sub(r'[^0-9]', '', str(sheet_data[matched_row][28])))  # AC열
            
            # 4. 잔고 차이 계산
            stock_diff = hts_stock_q - best_match  # 양수: 초과보유, 음수: 부족보유
            
            # 5. 주문량 보정
            adjusted_buy_q = max(0, original_buy_q - stock_diff)   # 매수: 차이만큼 차감
            adjusted_sell_q = max(0, original_sell_q + stock_diff)  # 매도: 차이만큼 추가
            
            # 6. 결과 로깅
            if stock_diff == 0:
                log(f"🎯 완벽 매칭: {tier_name}티어 ({hts_stock_q}주)", "✅")
            else:
                log(f"🎯 범위 매칭: {tier_name}티어 (시트:{best_match}주 / HTS:{hts_stock_q}주 / 차이:{stock_diff:+d}주)", "🔍")
                log(f"   📊 주문량 보정: 매수 {original_buy_q}→{adjusted_buy_q}주 / 매도 {original_sell_q}→{adjusted_sell_q}주", "🔍")
                
                # 차이가 과다한 경우 경고
                if abs(stock_diff) > 50:
                    log(f"⚠️ 잔고 차이 과다: {stock_diff:+d}주 (50주 초과)", "🚨")
            
            # 7. 티어 데이터 반환
            tier_data = {
                'matched_row': matched_row + 1,
                'row_idx': matched_row + 1,
                'curr_tier': tier_name,
                'sheet_stock_q': best_match,
                'buy_p': clean_float(sheet_data[matched_row][25]),  # Z열 (매수가)
                'buy_q': adjusted_buy_q,  # 🔥 보정된 매수량
                'sell_p': clean_float(sheet_data[matched_row][27]),  # AB열 (매도가)
                'sell_q': adjusted_sell_q,  # 🔥 보정된 매도량
                'stock_diff': stock_diff,  # 잔고 차이
                'original_buy_q': original_buy_q,  # 원래 매수량 (참고용)
                'original_sell_q': original_sell_q  # 원래 매도량 (참고용)
            }
            
            return tier_data

        except Exception as e:
            log(f"티어 검색 오류: {e}", "❌")
            import traceback
            traceback.print_exc()
            return None

    def update_tier(self, ws, tier_name):
        """현재 티어를 시트에 업데이트 (K6)"""
        try:
            ws.update_cell(6, 11, tier_name)  # 6행 11열 = K6
            log(f"티어 업데이트 (K6): {tier_name}", "✅")
            return True
        except Exception as e:
            log(f"티어 업데이트 실패: {e}", "⚠️")
            return False

    def update_trade_count(self, ws, is_buy):
        """
        매매 체결 카운트 업데이트

        Args:
            ws: 워크시트
            is_buy: True면 매수, False면 매도
        """
        try:
            if is_buy:
                # K14 (매수 카운트)
                current = safe_int(ws.cell(14, 11).value)
                ws.update_cell(14, 11, current + 1)
                log(f"매수 카운트 업데이트: {current} → {current + 1}", "✅")
            else:
                # K16 (매도 카운트)
                current = safe_int(ws.cell(16, 11).value)
                ws.update_cell(16, 11, current + 1)
                log(f"매도 카운트 업데이트: {current} → {current + 1}", "✅")
            return True
        except Exception as e:
            log(f"카운트 업데이트 실패: {e}", "⚠️")
            return False
