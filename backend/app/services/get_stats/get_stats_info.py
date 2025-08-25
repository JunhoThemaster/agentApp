# get_stats_info.py
# -*- coding: utf-8 -*-
from typing import Any, Dict
from elasticsearch.exceptions import NotFoundError
from app.es.client import get_client

INDEX_NAME = "sessions_stats"

def get_stats_by_session(session_id: str, index_name: str = INDEX_NAME) -> Dict[str, Any]:
    """
    Elasticsearch에서 session_id로 통계 문서를 조회하고
    API 응답에 바로 쓸 수 있는 JSON(dict) 구조로 반환.
    """
    es = get_client()
    try:
        doc = es.get(index=index_name, id=session_id)
    except NotFoundError:
        return {
            "session_id": session_id,
            "found": False,
            "stats": None
        }

    src = doc.get("_source", {})
    return {
        "session_id": src.get("session_id"),
        "found": True,
        "stats": {
            "latency": src.get("stats", {}).get("latency", {}),
            "command": src.get("stats", {}).get("command", {}),
            "tracking_error": src.get("stats", {}).get("tracking_error", {}),
            "joint_velocity_diff": src.get("stats", {}).get("joint_velocity_diff", {}),
        }
    }
