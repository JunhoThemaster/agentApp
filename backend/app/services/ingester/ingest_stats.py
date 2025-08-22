import pandas as pd
from pathlib import Path
from app.es.client import get_client
from elasticsearch import helpers

CSV_PATH = "/home/dickson/문서/agentApp/backend/app/data/all_labs_merged.csv"

INDEX_NAME = "sessions_stats"

PAIR_COLS = [
    ("action/target_cartesian_position_col0", "observation/robot_state/cartesian_position_col0"),
    ("action/target_cartesian_position_col1", "observation/robot_state/cartesian_position_col1"),
    ("action/target_cartesian_position_col2", "observation/robot_state/cartesian_position_col2"),
    ("action/joint_velocity_col0", "observation/robot_state/joint_velocities_col0"),
    ("action/joint_velocity_col1", "observation/robot_state/joint_velocities_col1"),
    ("action/joint_velocity_col2", "observation/robot_state/joint_velocities_col2"),
]

def compute_stats(df: pd.DataFrame):
    stats = {
        "latency": {},
        "command": {},
        "tracking_error": {},
        "joint_velocity_diff": {},
    }

    # ✅ latency
    if "action/robot_state/prev_controller_latency_ms" in df.columns:
        stats["latency"]["action_prev"] = {
            "mean": df["action/robot_state/prev_controller_latency_ms"].mean(),
            "std": df["action/robot_state/prev_controller_latency_ms"].std(),
        }
    if "observation/robot_state/prev_controller_latency_ms" in df.columns:
        stats["latency"]["observation_prev"] = {
            "mean": df["observation/robot_state/prev_controller_latency_ms"].mean(),
            "std": df["observation/robot_state/prev_controller_latency_ms"].std(),
        }

    # ✅ command
    if "observation/robot_state/prev_command_successful" in df.columns:
        stats["command"]["success_rate"] = df["observation/robot_state/prev_command_successful"].mean()

    # ✅ position error (target vs observed)
    pos_diffs = []
    for a, o in PAIR_COLS[:3]:
        if a in df.columns and o in df.columns:
            pos_diffs.extend((df[a] - df[o]).dropna().tolist())
    if pos_diffs:
        s = pd.Series(pos_diffs)
        stats["tracking_error"] = {
            "mean": s.mean(),
            "std": s.std(),
        }

    # ✅ joint velocity diff
    vel_diffs = []
    for a, o in PAIR_COLS[3:]:
        if a in df.columns and o in df.columns:
            vel_diffs.extend((df[a] - df[o]).dropna().tolist())
    if vel_diffs:
        s = pd.Series(vel_diffs)
        stats["joint_velocity_diff"] = {
            "mean": s.mean(),
            "std": s.std(),
        }

    return stats

def ingest_stats():
    es = get_client()
    df = pd.read_csv(CSV_PATH)

    actions = []
    for session_id, group in df.groupby("session_id"):
        stats = compute_stats(group)
        actions.append({
            "_op_type": "index",
            "_index": INDEX_NAME,
            "_id": str(session_id),
            "_source": {
                "session_id": str(session_id),
                "stats": stats,
            }
        })

    helpers.bulk(es, actions)
    print(f"[OK] {len(actions)} sessions indexed into {INDEX_NAME}")

if __name__ == "__main__":
    ingest_stats()
