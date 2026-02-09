"""
HWID 생성 모듈
사용자의 메인보드 및 CPU 정보를 조합하여 고유 HWID 생성
"""

import wmi
import hashlib


def get_hwid():
    """사용자의 메인보드 및 CPU 정보를 조합하여 고유 HWID 생성"""
    try:
        c = wmi.WMI()
        board_id = ""
        cpu_id = ""

        # 메인보드 시리얼 번호 추출
        try:
            for board in c.Win32_BaseBoard():
                if board.SerialNumber:
                    board_id = board.SerialNumber.strip()
                    break
        except Exception as e:
            print(f"⚠️ 메인보드 정보 추출 실패: {e}")
            board_id = "UNKNOWN_BOARD"

        # CPU ID 추출
        try:
            for cpu in c.Win32_Processor():
                if cpu.ProcessorId:
                    cpu_id = cpu.ProcessorId.strip()
                    break
        except Exception as e:
            print(f"⚠️ CPU 정보 추출 실패: {e}")
            cpu_id = "UNKNOWN_CPU"

        # HWID 생성
        raw_hwid = f"{board_id}-{cpu_id}"
        hwid_hash = hashlib.sha256(raw_hwid.encode()).hexdigest().upper()

        # 앞의 16자리만 포맷팅 (4자리씩 끊어서)
        formatted_hwid = f"{hwid_hash[:4]}-{hwid_hash[4:8]}-{hwid_hash[8:12]}-{hwid_hash[12:16]}"
        
        return formatted_hwid

    except Exception as e:
        print(f"❌ HWID 생성 중 치명적 오류: {e}")
        return "UNKNOWN-HWID-ERROR"
