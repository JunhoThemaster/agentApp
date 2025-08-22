import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import json

def build_txt2txt_docs(csv_path: str):
    df = pd.read_csv(csv_path)

    pair_cols = [
        ("action/target_cartesian_position_col0", "observation/robot_state/cartesian_position_col0"),
        ("action/target_cartesian_position_col1", "observation/robot_state/cartesian_position_col1"),
        ("action/target_cartesian_position_col2", "observation/robot_state/cartesian_position_col2"),
        ("action/joint_velocity_col0", "observation/robot_state/joint_velocities_col0"),
        ("action/joint_velocity_col1", "observation/robot_state/joint_velocities_col1"),
        ("action/joint_velocity_col2", "observation/robot_state/joint_velocities_col2"),
    ]

    for act, obs in pair_cols:
        df[f"err::{act.split('/')[-1]}"] = df[act] - df[obs]

    def summarize_session(session_df):
        obs_vals = session_df[[c for _, c in pair_cols]].values.flatten()
        err_vals = session_df[[f"err::{act.split('/')[-1]}" for act, _ in pair_cols]].values.flatten()
        return {
            "obs_mean": float(np.nanmean(obs_vals)),
            "obs_std": float(np.nanstd(obs_vals)),
            "obs_range": float(np.nanmax(obs_vals) - np.nanmin(obs_vals)),
            "err_mean": float(np.nanmean(err_vals)),
            "err_std": float(np.nanstd(err_vals)),
            "err_max": float(np.nanmax(err_vals)),
        }

    stats = df.groupby("session_id").apply(summarize_session).reset_index(name="stats")
    session_summary = df.groupby("session_id")["video_summary"].first().reset_index()
    merged = pd.merge(stats, session_summary, on="session_id", how="left")

    koe5 = SentenceTransformer("nlpai-lab/KoE5")
    distiluse = SentenceTransformer("sentence-transformers/distiluse-base-multilingual-cased-v1")

    summaries = merged["video_summary"].fillna("").tolist()
    embeddings_koe5 = koe5.encode(summaries, convert_to_numpy=True, normalize_embeddings=True)
    embeddings_distiluse = distiluse.encode(summaries, convert_to_numpy=True, normalize_embeddings=True)

    docs = []
    for i, row in merged.iterrows():
        doc = {
            "session_id": row["session_id"],
            "video_summary": row["video_summary"],
            "observation_stats": {
                "mean": row["stats"]["obs_mean"],
                "std": row["stats"]["obs_std"],
                "range": row["stats"]["obs_range"],
            },
            "error_stats": {
                "mean": row["stats"]["err_mean"],
                "std": row["stats"]["err_std"],
                "max": row["stats"]["err_max"],
            },
            "embedding_koe5": embeddings_koe5[i].tolist(),
            "embedding_distiluse": embeddings_distiluse[i].tolist(),
        }
        docs.append(doc)

    return docs
