import pandas as pd

def extract_stats(df: pd.DataFrame):
    """세션 데이터프레임에서 Observation / Error 통계 계산"""
    obs_cols = [c for c in df.columns if "observation" in c]
    act_cols = [c for c in df.columns if "action" in c]

    obs_stats = {}
    for col in obs_cols:
        obs_stats[col] = {
            "mean": df[col].mean(),
            "var": df[col].var(),
            "min": df[col].min(),
            "max": df[col].max(),
        }

    err_stats = {}
    for a, o in zip(act_cols, obs_cols):
        err = df[a] - df[o]
        err_stats[f"{a}-{o}"] = {
            "mean": err.mean(),
            "std": err.std(),
            "max": err.max(),
        }

    return obs_stats, err_stats
