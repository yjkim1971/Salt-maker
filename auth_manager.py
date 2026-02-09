import datetime
import tkinter as tk
from tkinter import messagebox
from utils import log


class AuthManager:
    def __init__(self, sheet_manager):
        self.sm = sheet_manager
        # 영진님의 시트 정보
        self.auth_sheet_name = "salt_maker_License인증"
        self.auth_ws_name = "인증테스트"
    
    def register_new_user(self, user_hwid, user_name):
        """
        신규 사용자를 인증 시트에 자동 등록
        
        Args:
            user_hwid: 사용자 CPU 번호
            user_name: 사용자 이름
            
        Returns:
            bool: 등록 성공 여부
        """
        try:
            log(f"📝 신규 사용자 등록 시작: {user_name} ({user_hwid})", "🆕")
            
            # 인증 시트 열기
            if not hasattr(self.sm, 'client') or self.sm.client is None:
                log("❌ 구글 시트 클라이언트 연결 실패", "❌")
                return False
            
            auth_doc = self.sm.client.open(self.auth_sheet_name)
            auth_ws = auth_doc.worksheet(self.auth_ws_name)
            
            # 기존 데이터 확인 (중복 방지)
            auth_data = auth_ws.get_all_values()
            for row in auth_data:
                if row and len(row) > 0 and row[0].strip() == user_hwid:
                    log(f"⚠️ 이미 등록된 HWID: {user_hwid}", "⚠️")
                    return False
            
            # 새 행 추가 (A: HWID, B: 이름, C: 권한(빈칸), D: 만료일(빈칸))
            new_row = [user_hwid, user_name, "", ""]
            auth_ws.append_row(new_row)
            
            log(f"✅ 신규 사용자 등록 완료: {user_name}", "✅")
            return True
            
        except Exception as e:
            log(f"❌ 신규 사용자 등록 실패: {e}", "❌")
            import traceback
            traceback.print_exc()
            return False
    
    def show_registration_required_dialog(self, user_hwid, user_name):
        """
        신규 사용자 등록 안내 팝업 표시
        
        Args:
            user_hwid: 사용자 CPU 번호
            user_name: 사용자 이름
        """
        try:
            root = tk.Tk()
            root.withdraw()  # 메인 윈도우 숨기기
            
            message = (
                f"🆕 신규 사용자 등록 완료\n\n"
                f"사용자 이름: {user_name}\n"
                f"식별 코드: {user_hwid}\n\n"
                f"⚠️ 관리자에게 실행 권한을 요청하세요!\n\n"
                f"관리자가 권한을 부여하면\n"
                f"프로그램을 다시 실행할 수 있습니다."
            )
            
            messagebox.showwarning("실행 권한 필요", message)
            root.destroy()
            
        except Exception as e:
            log(f"⚠️ 팝업 표시 실패: {e}", "⚠️")
            print(f"\n{'='*50}")
            print(f"🆕 신규 사용자 등록 완료")
            print(f"사용자 이름: {user_name}")
            print(f"식별 코드: {user_hwid}")
            print(f"\n⚠️ 관리자에게 실행 권한을 요청하세요!")
            print(f"{'='*50}\n")

    def check_license(self, user_hwid):
        """
        영진님의 GoogleSheetManager(self.sm)를 활용한 라이선스 체크
        """
        try:
            log(f"🔑 라이선스 인증 중... (ID: {user_hwid})", "🛡️")

            # 1. 영진님의 시트 매니저에 있는 'client' 객체를 사용하여 인증 시트 열기
            if not hasattr(self.sm, 'client') or self.sm.client is None:
                return False, "구글 시트 클라이언트가 연결되지 않았습니다."

            # 매매용 시트가 아닌 별도의 인증용 시트 파일을 엽니다.
            auth_doc = self.sm.client.open(self.auth_sheet_name)
            auth_ws = auth_doc.worksheet(self.auth_ws_name)

            # 모든 데이터 로드 (A열: HWID, B열: 이름, C열: 상태, D열: 만료일)
            auth_data = auth_ws.get_all_values()

            if not auth_data:
                return False, "인증 서버에서 데이터를 읽을 수 없습니다."

            # 2. HWID 매칭
            user_info = None
            for row in auth_data:
                if not row or len(row) < 1:
                    continue
                if row[0].strip() == user_hwid:
                    user_info = row
                    break

            if not user_info:
                # 🆕 미등록 사용자 → 자동 등록
                log(f"🆕 미등록 사용자 감지: {user_hwid}", "🆕")
                
                # 사용자 이름 입력 받기 (기본값: "신규사용자")
                try:
                    import tkinter as tk
                    from tkinter import simpledialog
                    
                    root = tk.Tk()
                    root.withdraw()
                    
                    user_name = simpledialog.askstring(
                        "신규 사용자 등록",
                        "사용자 이름을 입력하세요:",
                        initialvalue="신규사용자"
                    )
                    
                    root.destroy()
                    
                    if not user_name:
                        user_name = "신규사용자"
                        
                except:
                    user_name = "신규사용자"
                
                # 자동 등록 시도
                if self.register_new_user(user_hwid, user_name):
                    # 등록 완료 팝업
                    self.show_registration_required_dialog(user_hwid, user_name)
                    return False, "신규 사용자로 등록되었습니다.\n관리자의 승인을 기다려주세요."
                else:
                    return False, f"등록 처리 중 오류가 발생했습니다.\n식별 코드: {user_hwid}\n관리자에게 문의하세요."

            # 3. 데이터 검증 (C열: Status, D열: ExpireDate)
            if len(user_info) < 4:
                return False, "시트의 사용자 정보가 올바르지 않습니다. (필수 항목 누락)"

            status = str(user_info[2]).strip().upper()  # YES/NO
            expire_date_str = str(user_info[3]).strip()

            if status != "YES":
                return False, "사용 권한이 비활성화 상태입니다. 입금 확인이 필요합니다."

            # 4. 만료일 체크
            try:
                expire_date = datetime.datetime.strptime(expire_date_str, "%Y-%m-%d")
                if datetime.datetime.now() > expire_date:
                    return False, f"이용 기간이 만료되었습니다. ({expire_date_str} 종료)"
            except ValueError:
                return False, f"만료일 형식 오류: {expire_date_str}\n(YYYY-MM-DD 형식이 필요합니다.)"

            # 최종 승인
            user_name = user_info[1] if len(user_info) > 1 else "사용자"
            log(f"✅ 인증 성공! 만료일: {expire_date_str}", "✨")
            return True, f"반갑습니다, {user_name}님! 정식 사용자 인증되었습니다."

        except Exception as e:
            log(f"❌ 인증 과정 오류: {e}", "⚠️")
            return False, f"인증 서버 연결 실패: {str(e)}"
