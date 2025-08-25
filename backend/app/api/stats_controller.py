from fastapi import APIRouter
from app.services.get_stats.get_stats_info import get_stats_by_session

router = APIRouter()

@router.get("/api/stats/{session_id}")
def stats_api(session_id: str):
    return get_stats_by_session(session_id)
