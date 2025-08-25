from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from ..services.video_service import find_video_path

router = APIRouter()


# 비디오 경로 찾고 파일리스폰스 보내기 ... 이게 맞나 싶긴한데 일단 해보자
@router.get("/api/video/{session_id}/{camera_id}")
def stream_video(session_id: str, camera_id: str):
    video_path = find_video_path(session_id, camera_id)
    if not video_path:
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(video_path, media_type="video/mp4")
