from pathlib import Path
import re

BASE_DIR = Path("/home/user2/문서/agentApp")

# 리눅스에서는 파일이름에 : 가 들어가는게 가능하다고 한다 윈도우에서는 세션 파일 받을때 불가능해서 자동으로  : 를 _ 로 바꾼단다

def normalize_session_id(session_id: str) -> str:
    """
    ES에 저장된 session_id (Fri_Aug_18_12_06_27_2023) → 
    실제 폴더명 (Fri_Aug_18_12:06:27_2023) 변환
    """
    return re.sub(
        r'_(\d{2})_(\d{2})_(\d{2})_(\d{4})$',
        lambda m: f"_{m.group(1)}:{m.group(2)}:{m.group(3)}_{m.group(4)}",
        session_id
    )

def find_video_path(session_id: str, camera_id: str) -> str | None:
    """
    session_id와 camera_id를 기반으로 실제 mp4 경로를 찾는다.
    """
    
    real_session_id = normalize_session_id(session_id)
    for p in BASE_DIR.rglob(f"{camera_id}.mp4"):
        if real_session_id in str(p):
            return str(p)
    return None
