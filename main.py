import json
import os
import time
import traceback
from datetime import datetime
import psutil
import pyperclip
import pygetwindow as gw

from utils import DisplayManager, log, safe_int, safe_float, get_first_user_name

import config
from config import GRID_CONFIG_PATH, USER_NAME
from telegram_bot import telegram_bot
from google_sheet import GoogleSheetManager
from hts_controller import HTSController
from order_manager import OrderManager
from auth_manager import AuthManager
from hwid_generator import get_hwid
from telegram_bot import TelegramBot


def setup_telegram_config(sm, sheet_name):
    """지정된 시트의 E25(CHAT_ID), E27(TOKEN) 값을 config에 반영"""
    try:
        ws = sm.get_worksheet(sheet_name)
        if not ws:
            log(f"⚠️ '{sheet_name}' 시트를 찾을 수 없습니다.", "❌")
            return False

        res = ws.get("E25:E27")

        if len(res) >= 3:
            config.CHAT_ID = str(res[0][0]).strip()
            config.TELEGRAM_TOKEN = str(res[2][0]).strip()

            if config.CHAT_ID and config.TELEGRAM_TOKEN:
                log(f"✅ 텔레그램 설정 로드 완료 (시트: {sheet_name})", "🔔")
                return True

        log(f"⚠️ '{sheet_name}' 시트의 E25 또는 E27 셀이 비어있습니다.", "⚠️")
        return False
    except Exception as e:
        log(f"❌ 텔레그램 설정 로드 중 오류: {e}", "⚠️")
        return False


class SaltMaker:
    """자동매매 메인 클래스"""

    def __init__(self):
        self.display = DisplayManager()
        self.sheet_manager = GoogleSheetManager()
        self.hts = HTSController()
        self.telegram_manager = TelegramBot()
        self.order_manager = OrderManager(self.hts, self.telegram_manager)
        self.executed_logins = set()
        self.hts_status = ""
        self.hts_process_names = ["NFRunLite.exe", "nk_speed.exe", "v_trade.exe", "KHOpenAPI.exe", "nfstarter.exe"]
        
        # 🔥 각 그리드 매매 카드의 마지막 실행 시간 추적
        self.last_execution_times = {}  # {sheet_name: timestamp}

    def is_hts_on_top(self):
        """현재 화면 맨 위에 HTS가 떠 있는지 확인"""
        try:
            active_window = gw.getActiveWindow()
            if active_window is None:
                return False
            title = active_window.title
            return "영웅문" in title or "Global" in title
        except Exception as e:
            log(f"화면 확인 중 오류: {e}", "⚠️")
            return False

    def is_hts_active(self):
        """현재 윈도우의 포커스가 HTS인지 확인"""
        try:
            active_window = gw.getActiveWindow()
            if active_window is None:
                return False
            title = active_window.title
            return "영웅문" in title or "Global" in title
        except Exception as e:
            log(f"포커스 확인 중 오류: {e}", "⚠️")
            return False

    def is_hts_running(self):
        """HTS 프로세스 체크"""
        for _ in range(3):
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] in self.hts_process_names:
                        return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            time.sleep(1)
        return False

    def check_health(self):
        """HTS 상태 점검 및 복구"""
        if self.hts_status == "EXECUTED":
            if not self.is_hts_running():
                log("🚨 HTS 종료 감지! 복구 모드로 진입합니다.", "⚠️")
                telegram_bot.send_error_notification("🚨 HTS 종료 감지. Salt Maker 재접속 시도.")
                self.hts_status = ""
                self.executed_logins.clear()
                return False
        return True

    def check_kiwoom_blackout_time(self):
        """키움증권 주문 불가 시간(오후 5시~6시) 체크"""
        import datetime

        now = datetime.datetime.now()

        # 한국 시간 기준 오후 5시(17시)일 때 True 반환
        if now.hour == 17:
            return True
        return False

    def check_and_reset_daily_stats(self, ws):
        """아침 9시~10시 사이 첫 로그인 시 통계 초기화 (K21 날짜 체크)"""
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')

        if 9 <= now.hour < 10:
            try:
                last_reset_date = ws.acell('K21').value

                if last_reset_date != today_str:
                    reset_data = [[0], [0], [0], [0]]
                    ws.update(range_name='K14:K17', values=reset_data)
                    ws.update(range_name='K21', values=[[today_str]])

                    log(f"☀️ {today_str} 일일 통계 초기화 완료 (K21 기록)", "🔄")

                    self.telegram_manager.send_message(
                        f"☀️ 좋은 아침입니다!\n장 시작을 위해 통계를 초기화했습니다.\n(오늘 날짜: {today_str})"
                    )
            except Exception as e:
                log(f"❌ 아침 초기화 중 오류 발생: {e}", "⚠️")

    def load_tasks(self):
        """작업 파일 로드"""
        if not os.path.exists(GRID_CONFIG_PATH):
            return []
        try:
            with open(GRID_CONFIG_PATH, 'r', encoding='utf-8') as f:
                tasks = json.load(f)
            return list(tasks.values()) if isinstance(tasks, dict) else list(tasks)
        except Exception as e:
            log(f"작업 파일 로드 오류: {e}", "❌")
            return []

    def handle_auto_login(self, task):
        """자동 로그인 처리 - 구분자 ' / ' 통일"""
        try:
            status = task.get('status')
            details = task.get('details', "")
            items = [i.strip() for i in details.split(' / ')]  # 🔥 구분자 통일

            if len(items) >= 5:
                user_id, cert_order, start_time, hts_path, cert_pw = items[:5]
                if user_id in self.executed_logins or self.hts_status == "EXECUTED":
                    return

                now_time = datetime.now().strftime('%H:%M:%S')
                should_run = (status == "RUNNING") or (status == "READY" and now_time >= start_time) or (status == "EXECUTED")

                if should_run and os.path.exists(hts_path):
                    # 기존 HTS 정리
                    for proc in psutil.process_iter(['name']):
                        try:
                            if proc.info['name'] in self.hts_process_names:
                                proc.kill()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            continue
                    time.sleep(2)

                    log(f"HTS 로그인 시도 중... (사용자: {user_id})", "🔑")
                    if self.hts.login(hts_path, cert_order, cert_pw, user_id):
                        self.hts_status = "EXECUTED"
                        self.executed_logins.add(user_id)
                        time.sleep(35)
                        self.hts.connect_main_window()
                        self.hts.clear_screen()
                        self.hts.open_and_maximize_2220()
                        telegram_bot.send_login_notification(user_id, success=True)
                        log("HTS 로그인 및 화면 설정 완료", "✅")
        except Exception as e:
            log(f"로그인 처리 오류: {e}", "❌")
            traceback.print_exc()

    def handle_grid_trading(self, task):
        """매매 사이클 처리 - 구분자 ' / ' 통일"""
        sheet_name = None
        try:
            # 🔥 PAUSED 상태 체크 (최우선)
            status = task.get('status', 'READY')
            
            if status == "PAUSED":
                # 비활성화 상태면 완전히 건너뜀
                details = task.get('details', "")
                items = [i.strip() for i in details.split(' / ')]
                sheet_name = items[0] if items else "Unknown"
                log(f"⏸️ {sheet_name}: 비활성화 상태 - 건너뜀", "💤")
                return
            
            details = task.get('details', "")
            items = [i.strip() for i in details.split(' / ')]  # 🔥 구분자 통일
            if len(items) < 4:
                return

            sheet_name, start_t, end_t, interval = items[:4]
            interval_sec = safe_int(interval, 60)  # 간격 (초)
            now_t = datetime.now().strftime('%H:%M:%S')
            current_time = time.time()

            # 🔥 개별 간격 체크 (RUNNING 상태가 아닐 때만)
            if status != "RUNNING":
                last_exec_time = self.last_execution_times.get(sheet_name, 0)
                elapsed = current_time - last_exec_time
                
                if last_exec_time > 0 and elapsed < interval_sec:
                    remaining = interval_sec - int(elapsed)
                    log(f"⏱️ {sheet_name}: 간격 대기 중 ({remaining}초 남음)", "💤")
                    return

            # 🔥 RUNNING 상태면 시간 무시하고 즉시 실행
            # 🔥 READY 상태면 시간 체크
            is_work = (start_t <= now_t <= end_t) if start_t <= end_t else (now_t >= start_t or now_t <= end_t)
            
            if not is_work and status != "RUNNING":
                log(f"⏰ {sheet_name}: 작업 시간이 아닙니다. 건너뜁니다. (현재: {now_t})", "💤")
                return
            
            if status == "RUNNING":
                log(f"🔥 {sheet_name}: RUNNING 상태 - 즉시 실행!", "🚀")
            
            # 🔥 실행 시간 기록 (실행 직전)
            self.last_execution_times[sheet_name] = current_time

            sheet_data_obj = self.sheet_manager.load_trading_data(sheet_name)
            if not sheet_data_obj:
                log(f"❌ {sheet_name}: 시트 데이터 로드 실패", "❌")
                return

            ticker = sheet_data_obj['ticker']
            ws = sheet_data_obj['worksheet']
            self.check_and_reset_daily_stats(ws)

            log(f"📡 시트({sheet_name}) 처리 시작: {ticker}", "📡")

            if not self.hts.input_ticker(ticker):
                log(f"❌ {sheet_name}: 종목 입력 실패", "❌")
                return
            time.sleep(1.5)

            if not self.hts.select_account(sheet_data_obj['acc_cnt']):
                log(f"❌ {sheet_name}: 계좌 선택 실패", "❌")
                return
            time.sleep(1.0)

            now_price = self.hts.get_current_price(ticker)
            hts_stock_q = self.hts.get_stock_quantity(ticker)
            
            if now_price is None or hts_stock_q is None:
                log(f"❌ {sheet_name}: 현재가 또는 잔고 조회 실패", "❌")
                return

            # 🔥 K8(현재가) 실시간 업데이트
            try:
                ws.update('K8', [[now_price]])
                log(f"✅ K8(현재가) 업데이트: {now_price}", "🔍")
            except Exception as e:
                log(f"⚠️ K8 업데이트 실패: {e}", "⚠️")

            log(f"📊 현재가: {now_price} / HTS 잔고: {hts_stock_q}", "🔍")

            # 🔥 체결 감지 및 K12/K14/K16 자동 업데이트
            prev_hts_stock_q = sheet_data_obj.get('sheet_stock_q', hts_stock_q)  # 이전 HTS 잔고 (시트 K10)
            stock_change = hts_stock_q - prev_hts_stock_q  # 잔고 변화량
            
            if stock_change != 0:
                log(f"🔔 체결 감지! 잔고 변화: {prev_hts_stock_q}주 → {hts_stock_q}주 (변화량: {stock_change:+d}주)", "💰")
                
                try:
                    # K12에 차이 기록
                    ws.update('K12', [[stock_change]])
                    log(f"✅ K12 업데이트: {stock_change:+d}주", "✅")
                    
                    # 매수 체결 (잔고 증가)
                    if stock_change > 0:
                        current_buy_count = int(ws.acell('K14').value or 0)
                        ws.update('K14', [[current_buy_count + 1]])
                        log(f"💰 매수 체결! K14(매수 횟수): {current_buy_count} → {current_buy_count + 1}", "💰")
                    
                    # 매도 체결 (잔고 감소)
                    elif stock_change < 0:
                        current_sell_count = int(ws.acell('K16').value or 0)
                        ws.update('K16', [[current_sell_count + 1]])
                        log(f"💰 매도 체결! K16(매도 횟수): {current_sell_count} → {current_sell_count + 1}", "💰")
                    
                    # K10(HTS 잔고) 업데이트
                    ws.update('K10', [[hts_stock_q]])
                    log(f"✅ K10 업데이트: {hts_stock_q}주", "✅")
                    
                except Exception as e:
                    log(f"⚠️ 체결 데이터 업데이트 실패: {e}", "⚠️")
            
            # 🔥 차이 해소 확인 (범위 매칭으로 티어 찾은 후)
            tier_data = self.sheet_manager.find_tier_by_quantity(sheet_data_obj['sheet_data'], hts_stock_q)
            
            if tier_data:
                stock_diff = tier_data.get('stock_diff', 0)  # HTS 잔고 - 시트 티어 잔고
                
                # 차이가 해소되었으면 K12를 0으로 초기화
                if stock_diff == 0:
                    try:
                        current_k12 = ws.acell('K12').value
                        if current_k12 and current_k12 != '0' and current_k12 != 0:
                            ws.update('K12', [[0]])
                            log(f"🎯 차이 해소! K12 초기화: {current_k12} → 0", "✅")
                    except Exception as e:
                        log(f"⚠️ K12 초기화 실패: {e}", "⚠️")

            last_tier = ws.acell('E12').value
            sheet_buy_stop = ws.acell('E18').value.upper() == 'TRUE'
            sheet_sell_stop = ws.acell('E20').value.upper() == 'TRUE'

            # 기본값 설정
            curr_tier_name = "매칭실패"
            buy_p, buy_q, sell_p, sell_q = 0, 0, 0, 0
            buy_status, sell_status = "STAY", "STAY"
            buy_count, sell_count = 0, 0

            # tier_data는 이미 위에서 가져왔음 (중복 방지)
            if tier_data:
                curr_tier_name = tier_data['curr_tier']
                buy_p, buy_q = tier_data['buy_p'], tier_data['buy_q']  # 🔥 이미 보정된 값
                sell_p, sell_q = tier_data['sell_p'], tier_data['sell_q']  # 🔥 이미 보정된 값
                stock_diff = tier_data.get('stock_diff', 0)  # 잔고 차이
                original_buy_q = tier_data.get('original_buy_q', buy_q)
                original_sell_q = tier_data.get('original_sell_q', sell_q)

                buy_chk = False
                sell_chk = False

                try:
                    sell_count = int(ws.acell('K14').value or 0)
                    buy_count = int(ws.acell('K16').value or 0)
                except:
                    sell_count = 0
                    buy_count = 0

                # 🔥 잔고 차이 기반 자동 차단 로직
                if stock_diff != 0:
                    # 잔고가 초과 (예: HTS 37주, 시트 30주 → +7주 초과)
                    if stock_diff > 0 and stock_diff > original_buy_q:
                        try:
                            ws.update_acell('E18', True)
                            log(f"🔒 {sheet_name}: 잔고 초과({stock_diff:+d}주) > 매수량({original_buy_q}주) → E18 자동 활성화", "🔒")
                        except Exception as e:
                            log(f"⚠️ E18 업데이트 실패: {e}", "⚠️")
                    
                    # 잔고가 부족 (예: HTS 20주, 시트 30주 → -10주 부족)
                    elif stock_diff < 0 and abs(stock_diff) > original_sell_q:
                        try:
                            ws.update_acell('E20', True)
                            log(f"🔒 {sheet_name}: 잔고 부족({stock_diff:+d}주) > 매도량({original_sell_q}주) → E20 자동 활성화", "🔒")
                        except Exception as e:
                            log(f"⚠️ E20 업데이트 실패: {e}", "⚠️")

                self.sheet_manager.update_tier(ws, curr_tier_name)

                log(f"🚀 주문 관리자로 데이터 전달: {ticker}", "📢")
                log(f"👉 [전달값] 매수: {buy_p} ({buy_q}주) / 매도: {sell_p} ({sell_q}주)", "📢")
                if stock_diff != 0:
                    log(f"   ⚙️ 잔고 차이 보정 적용: {stock_diff:+d}주", "🔧")

                trade_result = self.order_manager.execute_trade_logic(
                    sheet_data=sheet_data_obj['sheet_data'],
                    ticker=ticker,
                    hts_stock_q=hts_stock_q,
                    sheet_stock_q=sheet_data_obj['sheet_stock_q'],
                    buy_p=float(buy_p),
                    buy_q=int(buy_q),
                    sell_p=float(sell_p),
                    sell_q=int(sell_q),
                    buy_chk=buy_chk,
                    sell_chk=sell_chk,
                    ws=ws,
                    last_tier=last_tier,
                    curr_tier=curr_tier_name,
                    sheet_buy_stop=sheet_buy_stop,
                    sheet_sell_stop=sheet_sell_stop,
                    curr_price=float(now_price),
                    buy_count=buy_count,
                    sell_count=sell_count,
                    avg_price=sheet_data_obj['avg_price']
                )

                if trade_result is None:
                    trade_result = {'buy_status': 'STAY', 'sell_status': 'STAY'}

                buy_status = trade_result.get('buy_status', 'STAY')
                sell_status = trade_result.get('sell_status', 'STAY')

                # 예수금 부족 자동 차단
                if buy_status == "LACK_OF_MONEY_POPUP":
                    try:
                        ws.update_acell('E18', True)
                        log(f"🔒 {sheet_name}: 예수금 부족 -> E18 자동 활성화 완료", "🔒")
                    except Exception as e:
                        log(f"시트 업데이트 실패 (E18): {e}", "❌")

                log(f"✅ {sheet_name} 처리 완료 (티어: {curr_tier_name})", "➡️")

            else:
                buy_status = "⚠️티어미매칭"
                log(f"⚠️ {sheet_name}: HTS 잔고({hts_stock_q})와 일치하는 티어 없음", "⚠️")

            # 텔레그램 알림 발송
            telegram_bot.send_order_notification(
                sheet_name,
                ticker,
                curr_tier_name,
                hts_stock_q,
                buy_p,
                buy_q,
                sell_p,
                sell_q,
                now_price,
                buy_status,
                sell_status,
                last_tier,
                buy_count,
                sell_count
            )

        except Exception as e:
            log(f"매매 오류 ({sheet_name or 'Unknown'}): {e}", "❌")
            traceback.print_exc()

    def run(self, user_name="영진"):
        """메인 실행 루프"""
        try:
            self.display.change_resolution()
            log(f"{user_name}님의 Salt Maker 시작", "🚀")

            while True:
                # 1. 키움 블랙아웃 시간 체크 (17:00 ~ 18:00)
                if self.check_kiwoom_blackout_time():
                    msg = "⏳ [Salt Maker 안내]\n현재는 키움증권 주문 제한 시간(17:00~18:00)입니다.\n시스템 보호를 위해 18시까지 대기 후 작업을 재개합니다."
                    log(msg, "💤")

                    tg = getattr(self, 'telegram_manager', None) or getattr(self, 'telegram_bot', None)
                    if tg:
                        tg.send_message(msg)

                    # 18시 정각까지 대기
                    while datetime.datetime.now().hour == 17:
                        time.sleep(60)

                    resume_msg = "🚀 주문 제한 시간이 종료되었습니다. Salt Maker 다시 가동합니다!"
                    log(resume_msg, "✨")
                    if tg:
                        tg.send_message(resume_msg)

                    continue


                # HTS 상태 체크
                if not self.check_health():
                    log("HTS 복구 필요. 10초 후 재시도...", "⚠️")
                    time.sleep(10)
                    continue

                # 작업 파일 로드
                tasks = self.load_tasks()
                if not tasks:
                    log("작업 파일이 없습니다. 10초 후 재시도...", "⏳")
                    time.sleep(10)
                    continue

                # 첫 번째 카드의 interval 추출
                first_interval = 60
                try:
                    first_task = tasks[0]
                    items = [i.strip() for i in first_task.get('details', "").split(' / ')]  # 🔥 구분자 통일
                    if len(items) >= 4:
                        first_interval = int(items[3])
                except:
                    first_interval = 60

                log(f"========== 새 사이클 시작 (총 {len(tasks)}개 작업) ==========", "🔄")

                grid_tasks_count = 0
                cycle_interrupted = False

                for idx, task in enumerate(tasks, 1):
                    task_type = task.get('type')

                    if task_type == "자동 로그인":
                        if self.hts_status != "EXECUTED":
                            self.handle_auto_login(task)

                    elif task_type == "그리드 매매" and self.hts_status == "EXECUTED":
                        # HTS 화면 체크
                        if not self.is_hts_on_top():
                            log("🚨 HTS 화면 이탈 감지! 1분 대기 후 재시도...", "⚠️")
                            telegram_bot.send_message("⚠️ HTS 창이 가려졌습니다. 매매를 잠시 멈춥니다.")
                            time.sleep(60)
                            cycle_interrupted = True
                            break

                        grid_tasks_count += 1
                        log(f"--- 작업 {idx}/{len(tasks)}: 그리드 매매 #{grid_tasks_count} 시작 ---", "📌")
                        self.handle_grid_trading(task)
                        log(f"--- 작업 {idx}/{len(tasks)}: 완료 ---", "✅")

                if cycle_interrupted:
                    log("사이클 중단됨. 다음 사이클로 이동합니다.", "⚠️")
                    continue

                log(f"========== 사이클 완료 ({grid_tasks_count}개 종목 처리) ==========", "✅")
                
                # 🔥 개별 간격 방식: 빠른 체크 루프 (5초마다)
                log(f"⏰ 5초 후 다음 체크 사이클...", "⏰")
                time.sleep(5)

        except KeyboardInterrupt:
            log("사용자에 의해 프로그램이 종료되었습니다.", "🛑")
        except Exception as e:
            log(f"🚨 가동 중 오류 발생: {e}", "❌")
            traceback.print_exc()
        finally:
            self.display.restore_resolution()
            log("프로그램 종료. 화면 해상도 복구 완료.", "👋")


def main():
    try:
        log("1. 프로그램 초기화 중...", "🔍")
        sm = GoogleSheetManager()

        # task.json 로드 및 검증
        if not os.path.exists(GRID_CONFIG_PATH):
            log(f"❌ 설정 파일({GRID_CONFIG_PATH})을 찾을 수 없습니다.", "🚨")
            input("엔터를 누르면 종료합니다...")
            return

        first_sheet_name = None
        with open(GRID_CONFIG_PATH, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
            task_list = list(tasks.values()) if isinstance(tasks, dict) else tasks
            for t in task_list:
                if t.get('type') == "그리드 매매":
                    details = t.get('details', "")
                    if details:
                        first_sheet_name = [i.strip() for i in details.split(' / ')][0]  # 🔥 구분자 통일
                        break

        # 텔레그램 설정 로드
        if first_sheet_name:
            setup_telegram_config(sm, first_sheet_name)
        else:
            log("⚠️ '그리드 매매' 작업을 찾을 수 없어 기본 설정을 유지합니다.", "⚠️")

        # 라이선스 체크
        current_hwid = get_hwid()
        auth = AuthManager(sm)
        is_valid, msg = auth.check_license(current_hwid)

        if not is_valid:
            log(f"❌ 인증 실패: {msg}", "🚨")
            pyperclip.copy(current_hwid)
            input("종료하려면 엔터를 누르세요...")
            return

        # SaltMaker 실행
        log(f"✅ {msg}", "🚀")

        dynamic_user_name = get_first_user_name()
        bot = SaltMaker()
        log(f"🤖 {dynamic_user_name}님의 Salt Maker 객체 생성 완료. 실행을 시작합니다.", "✨")

        bot.run(dynamic_user_name)

    except Exception as e:
        log(f"🚨 메인 로직 실행 중 치명적 오류: {e}", "❌")
        traceback.print_exc()
        input("오류 발생으로 종료되었습니다. 엔터를 누르세요...")


if __name__ == "__main__":
    main()
