"""
HTS 제어 모듈
로그인, 화면 조작, 현재가/잔고 확인 담당
"""
import config
import time
import subprocess
import pyautogui
import pyperclip
import psutil  # 추가: kill_hts_processes()에서 사용
from pywinauto import Application, mouse
from datetime import datetime
import pygetwindow as gw

from config import (
    COORDS_TICKER_INPUT, COORDS_ACCOUNT_LIST, 
    COORDS_ACCOUNT_1, COORDS_ACCOUNT_2, COORDS_ACCOUNT_3,
    COORDS_ACCOUNT_4, COORDS_ACCOUNT_5, COORDS_ACCOUNT_6,
    COORDS_ACCOUNT_7, COORDS_ACCOUNT_8, COORDS_ACCOUNT_9,
    COORDS_PRICE_TAB, COORDS_AUTO_PRICE, COORDS_PRICE_FIELD,
    COORDS_QUANTITY_TAB, COORDS_AUTO_100, COORDS_QUANTITY_FIELD,
    WAIT_TIME
)
from utils import log, safe_float, safe_int


class HTSController:
    """HTS 제어 클래스"""

    def __init__(self):
        self.app = None
        self.main_dlg = None
        self.screen_2220 = None
        self.status = "NOT_CONNECTED"
        self.hts_process_names = ["NFRunLite.exe", "nk_speed.exe", "v_trade.exe", "KHOpenAPI.exe", "nfstarter.exe"]

    def kill_hts_processes(self):
        """기존 HTS 프로세스 완전 종료 (복구 시 사용)"""
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in self.hts_process_names:
                    proc.kill()
                    log(f"기존 프로세스 종료: {proc.info['name']}", "🧹")
            except:
                continue
        time.sleep(2)

    def login(self, hts_path, cert_order, cert_pw, user_id):
        """
        HTS 로그인 실행

        Args:
            hts_path: HTS 실행 파일 경로
            cert_order: 인증서 순서
            cert_pw: 인증서 비밀번호
            user_id: 사용자 ID

        Returns:
            bool: 성공 여부
        """
        try:
            log(f"HTS 실행 시작: {hts_path}", "🚀")

            # HTS 실행
            subprocess.Popen(hts_path)
            time.sleep(WAIT_TIME["LOGIN"])

            # 인증서 창 연결
            app = Application(backend="win32").connect(title_re="인증서 선택.*", timeout=25)
            dlg = app.window(title_re="인증서 선택.*")
            dlg.set_focus()

            # 인증서 선택
            cert_list = dlg.child_window(class_name="SysListView32")
            cert_list.click_input()
            cert_list.type_keys("{HOME}")

            for _ in range(int(cert_order) - 1):
                cert_list.type_keys("{DOWN}")

            # 비밀번호 입력
            mouse.click(coords=(703, 508))
            time.sleep(WAIT_TIME["SHORT"])
            dlg.type_keys(cert_pw, with_spaces=True)
            dlg.child_window(title="인증서 선택(확인)").click_input()

            log(f"[{user_id}] 로그인 요청 성공", "✅")
            time.sleep(WAIT_TIME["CERT"])

            self.status = "LOGGED_IN"
            return True

        except Exception as e:
            log(f"로그인 실패: {e}", "❌")
            self.status = "LOGIN_FAILED"
            return False

    def connect_main_window(self):
        """메인 HTS 창에 연결"""
        try:
            self.app = Application(backend="win32").connect(
                title_re=".*영웅문Global.*",
                timeout=40,
                found_index=0
            )
            self.main_dlg = self.app.window(title_re=".*영웅문Global.*", found_index=0)
            self.main_dlg.set_focus()
            log("메인 창 연결 성공", "✅")
            return True
        except Exception as e:
            log(f"메인 창 연결 실패: {e}", "❌")
            return False

    def open_and_maximize_2220(self):
        """2220 화면 열기 및 최대화"""
        try:
            # 기존 2220 화면 체크
            try:
                self.screen_2220 = self.main_dlg.child_window(title_re=".*2220.*", found_index=0)
                if self.screen_2220.exists():
                    log("2220 화면 이미 존재", "ℹ️")
                    self.screen_2220.set_focus()
                else:
                    raise Exception("창 없음")
            except:
                # 새로 열기
                log("2220 화면 새로 호출", "🔄")
                mouse.click(coords=(26, 88))
                time.sleep(WAIT_TIME["MEDIUM"])
                self.main_dlg.type_keys("2220{ENTER}", pause=0.1)
                time.sleep(WAIT_TIME["SCREEN_LOAD"])
                self.screen_2220 = self.main_dlg.child_window(title_re=".*2220.*", found_index=0)

            # 최대화
            if self.screen_2220.get_show_state() != 3:
                try:
                    self.screen_2220.set_focus()
                    self.screen_2220.maximize()
                    log("2220 표준 최대화 성공", "✅")
                except:
                    mouse.click(coords=(1016, 250))
                    time.sleep(WAIT_TIME["MEDIUM"])
                    log("좌표 클릭 최대화 성공", "✅")

            # 최대화 후 1초 대기
            time.sleep(1.0)
            return True

        except Exception as e:
            log(f"2220 화면 관리 오류: {e}", "❌")
            return False

    def is_hts_on_top(self):
        """현재 화면 맨 위에 HTS가 떠 있는지 확인"""
        try:
            active_window = gw.getActiveWindow()
            if active_window is None:
                return False
            title = active_window.title
            return "영웅문" in title or "Global" in title
        except:
            return False

    def input_ticker(self, ticker):
        """
        종목 입력

        Args:
            ticker: 종목 코드
        """
        try:
            log(f"티커 입력: {ticker}", "⌨️")

            # 좌측 종목 필드 클릭
            time.sleep(5)
            mouse.click(coords=COORDS_TICKER_INPUT)
            time.sleep(WAIT_TIME["SHORT"])

            # 기존 텍스트 삭제 후 입력
            self.main_dlg.type_keys('^a{BACKSPACE}')
            time.sleep(0.1)
            self.main_dlg.type_keys(ticker + "{ENTER}", with_spaces=True)
            time.sleep(0.8)

            log(f"{ticker} 좌측 종목 조회 완료", "✅")
            return True

        except Exception as e:
            log(f"티커 입력 오류: {e}", "❌")
            return False

    def select_account(self, acc_cnt):
        """
        계좌 선택

        Args:
            acc_cnt: 계좌 순번 (1~9)
        """
        try:
            log(f"계좌 선택: {acc_cnt}번", "🎯")

            # 계좌 리스트 열기
            mouse.click(coords=COORDS_ACCOUNT_LIST)
            time.sleep(WAIT_TIME["MEDIUM"])

            # 계좌 번호에 따라 클릭
            cnt_num = safe_int(acc_cnt, 8)
            
            account_coords = {
                1: COORDS_ACCOUNT_1,
                2: COORDS_ACCOUNT_2,
                3: COORDS_ACCOUNT_3,
                4: COORDS_ACCOUNT_4,
                5: COORDS_ACCOUNT_5,
                6: COORDS_ACCOUNT_6,
                7: COORDS_ACCOUNT_7,
                8: COORDS_ACCOUNT_8,
                9: COORDS_ACCOUNT_9
            }
            
            mouse.click(coords=account_coords[cnt_num])
            log(f"✅ {cnt_num}번 계좌 선택", "✅")

            time.sleep(WAIT_TIME["MEDIUM"])
            log("계좌 선택 완료", "✅")
            return True

        except Exception as e:
            log(f"계좌 선택 오류: {e}", "❌")
            return False

    def get_current_price(self, ticker):
        """
        현재가 조회

        Returns:
            str: 현재가 (소수점 2자리)
        """
        try:
            # 1. 가격 탭 클릭
            pyautogui.click(*COORDS_PRICE_TAB)
            time.sleep(WAIT_TIME["MEDIUM"])

            # 2.1 종목 입력 필드 클릭
            mouse.click(coords=config.COORDS_TICKER1_INPUT)
            time.sleep(0.5)

            # 2.2. 기존 텍스트 전체 선택 후 삭제
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.2)

            # 2.3. ticker 값을 직접 타이핑
            pyautogui.write(ticker, interval=0.1)
            time.sleep(0.2)

            # 2.4. 엔터키로 조회 확정
            pyautogui.press('enter')

            log(f"⌨️ 티커 입력 완료: {ticker}", "✅")
            time.sleep(1.5)

            # 3. 자동 현재가 체크
            pyautogui.click(*COORDS_AUTO_PRICE)
            time.sleep(WAIT_TIME["MEDIUM"])

            # 4. 가격 필드 복사
            pyautogui.click(*COORDS_PRICE_FIELD)
            time.sleep(WAIT_TIME["MEDIUM"])
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.7)

            # 5. 자동 현재가 체크 해제
            pyautogui.click(406, 288)
            time.sleep(WAIT_TIME["MEDIUM"])

            # 클립보드 데이터 정제
            raw_data = pyperclip.paste().strip()

            if any(char.isdigit() for char in raw_data):
                filtered_price = ''.join(c for c in raw_data if c.isdigit() or c == '.')
                now_price = "{:.2f}".format(safe_float(filtered_price))
            else:
                now_price = "0.00"

            log(f"현재가 조회: {now_price} (원본: {raw_data})", "💰")
            return now_price

        except Exception as e:
            log(f"현재가 조회 오류: {e}", "❌")
            return "0.00"

    def get_stock_quantity(self, ticker):
        """
        보유 수량 조회

        Returns:
            int: 보유 수량
        """
        try:
            # 1. 수량 탭 클릭
            pyautogui.click(*COORDS_QUANTITY_TAB)
            time.sleep(WAIT_TIME["MEDIUM"])

            # 2.1 종목 입력 필드 클릭
            mouse.click(coords=config.COORDS_TICKER1_INPUT)
            time.sleep(0.5)

            # 2.2. 기존 텍스트 전체 선택 후 삭제
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.2)

            # 2.3. ticker 값을 직접 타이핑
            pyautogui.write(ticker, interval=0.1)
            time.sleep(0.2)

            # 2.4. 엔터키로 조회 확정
            pyautogui.press('enter')

            log(f"⌨️ 티커 입력 완료: {ticker}", "✅")
            time.sleep(1.5)

            # 3. 자동 100% 체크
            pyautogui.click(*COORDS_AUTO_100)
            time.sleep(WAIT_TIME["MEDIUM"])

            # 4. 수량 필드 복사
            pyautogui.click(*COORDS_QUANTITY_FIELD)
            time.sleep(WAIT_TIME["MEDIUM"])
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.7)

            # 클립보드 데이터 정제
            raw_stock_data = pyperclip.paste().strip()

            if any(char.isdigit() for char in raw_stock_data):
                clean_stock_q = ''.join(c for c in raw_stock_data if c.isdigit())
                hts_stock_q = safe_int(clean_stock_q)
            else:
                hts_stock_q = 0

            # 4. 자동 100% 체크 해제
            pyautogui.click(*COORDS_AUTO_100)
            time.sleep(WAIT_TIME["MEDIUM"])

            log(f"보유 수량: {hts_stock_q}주 (원본: {raw_stock_data})", "📊")
            return hts_stock_q

        except Exception as e:
            log(f"수량 조회 오류: {e}", "❌")
            return 0

    def clear_screen(self, coord=(994, 628)):
        """
        화면 초기화 (우클릭 메뉴)

        Args:
            coords=coord_clear: 우클릭할 좌표
        """
        try:
            log("화면 클리어 시작", "🖱️")

            # 좌표 클릭
            mouse.click(coords=coord)
            time.sleep(WAIT_TIME["SHORT"])

            # 우클릭
            mouse.click(button='right', coords=coord)
            time.sleep(WAIT_TIME["MEDIUM"])

            # 메뉴 항목 클릭
            mouse.click(coords=(1100, 591))

            log("화면 클리어 완료", "✅")
            return True

        except Exception as e:
            log(f"화면 클리어 오류: {e}", "⚠️")
            return False
