# -*- coding: utf-8 -*-
import math
from typing import Dict, Any, List, Tuple

import pandas as pd
from elasticsearch import helpers
from elasticsearch.exceptions import NotFoundError, RequestError

from app.es.client import get_client
from app.services.env_loader import env_loader  


# 설정
BASE_DIR = env_loader.env_loader()  
CSV_PATH = f"{BASE_DIR}/data/all_labs_merged.csv"
INDEX_NAME = "sessions_stats"

PAIR_COLS: List[Tuple[str, str]] = [
    ("action/target_cartesian_position_col0", "observation/robot_state/cartesian_position_col0"),
    ("action/target_cartesian_position_col1", "observation/robot_state/cartesian_position_col1"),
    ("action/target_cartesian_position_col2", "observation/robot_state/cartesian_position_col2"),
    ("action/joint_velocity_col0", "observation/robot_state/joint_velocities_col0"),
    ("action/joint_velocity_col1", "observation/robot_state/joint_velocities_col1"),
    ("action/joint_velocity_col2", "observation/robot_state/joint_velocities_col2"),
]


# 유틸
def _to_py_float(x) -> float:
    """numpy.float32/64 → 파이썬 float (NaN 방지). ES는 NaN을 거부하므로 None으로 치환."""
    try:
        if x is None:
            return None
        if isinstance(x, (float, int)):
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return None
            return float(x)
        # numpy 타입 등
        xf = float(x)
        if math.isnan(xf) or math.isinf(xf):
            return None
        return xf
    except Exception:
        return None


def _agg_series(values: List[float]) -> Dict[str, Any]:
    """평균/표준편차 계산(비어있으면 None)."""
    if not values:
        return {"mean": None, "std": None}
    s = pd.Series(values)
    return {
        "mean": _to_py_float(s.mean()),
        "std": _to_py_float(s.std()),
    }


# 통계 계산
def compute_stats(df: pd.DataFrame) -> Dict[str, Any]:
    stats: Dict[str, Any] = {
        "latency": {},
        "command": {},
        "tracking_error": {},
        "joint_velocity_diff": {},
    }

    #  latency
    if "action/robot_state/prev_controller_latency_ms" in df.columns:
        s = df["action/robot_state/prev_controller_latency_ms"].dropna()
        stats["latency"]["action_prev"] = _agg_series(s.tolist())

    if "observation/robot_state/prev_controller_latency_ms" in df.columns:
        s = df["observation/robot_state/prev_controller_latency_ms"].dropna()
        stats["latency"]["observation_prev"] = _agg_series(s.tolist())

    #  command success rate
    if "observation/robot_state/prev_command_successful" in df.columns:
        s = df["observation/robot_state/prev_command_successful"].dropna()
        stats["command"]["success_rate"] = _to_py_float(s.mean()) if not s.empty else None

    #  position error (target vs observed)
    pos_diffs: List[float] = []
    for a, o in PAIR_COLS[:3]:
        if a in df.columns and o in df.columns:
            pos_diffs.extend((df[a] - df[o]).dropna().tolist())
    stats["tracking_error"] = _agg_series(pos_diffs)

    #  joint velocity diff
    vel_diffs: List[float] = []
    for a, o in PAIR_COLS[3:]:
        if a in df.columns and o in df.columns:
            vel_diffs.extend((df[a] - df[o]).dropna().tolist())
    stats["joint_velocity_diff"] = _agg_series(vel_diffs)

    return stats


# 인덱싱
def ingest_stats(skip_existing: bool = True) -> None:
    """
    skip_existing=True 이면, 동일 _id(session_id)가 이미 있으면 생성 스킵.
    - 구현: _op_type="create" 사용 → 존재 시 409 충돌 → errors로 수집 → 스킵 집계
    """
    es = get_client()
    df = pd.read_csv(CSV_PATH)

    actions = []
    op_type = "create" if skip_existing else "index"

    for session_id, group in df.groupby("session_id"):
        stats = compute_stats(group)
        actions.append({
            "_op_type": op_type,              #  create → 없을 때만 생성
            "_index": INDEX_NAME,
            "_id": str(session_id),
            "_source": {
                "session_id": str(session_id),
                "stats": stats,
            }
        })

    success, errors = helpers.bulk(
        es,
        actions,
        raise_on_error=False,   # 충돌/에러 발생해도 전체 진행
        stats_only=False
    )

    # 409(conflict) 스킵 집계
    skipped = 0
    other_errors = 0
    for e in errors:
        # bulk 에러 구조: {'create': {'_index':..., 'status': 409, 'error': {...}}}
        if isinstance(e, dict):
            rec = e.get("create") or e.get("index") or e.get("update") or {}
            if rec.get("status") == 409:
                skipped += 1
            else:
                other_errors += 1
        else:
            other_errors += 1

    print(f"[OK] indexed: {success}, skipped(existing): {skipped}, errors: {other_errors}")


if __name__ == "__main__":
    ingest_stats(skip_existing=True)
