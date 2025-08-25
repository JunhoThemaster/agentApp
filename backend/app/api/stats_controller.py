from fastapi import APIRouter, HTTPException
from app.services.get_stats.get_stats_info import get_stats_by_session

router = APIRouter()

@router.get("/api/stats/{session_id}")
def read_stats(session_id: str):
    res = get_stats_by_session(session_id)
    if not res.get("found"):
        # 필요 없으면 200으로 내려도 됨
        raise HTTPException(status_code=404, detail=f"session_id '{session_id}' not found")
    return res