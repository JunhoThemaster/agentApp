
from typing import List, Dict, Any
import numpy as np
import pandas as pd
from pathlib import Path

from elasticsearch import helpers
from elasticsearch.exceptions import NotFoundError, RequestError
from PIL import Image
import cv2

from app.es.client import get_client
from app.services.env_loader import env_loader
from ...models_emb.embedder_siglip import UnifiedEmbedder
from app.services.video_service import find_video_path  

# 설정
BASE_DIR = env_loader.env_loader()  
CSV_PATH = f"{BASE_DIR}/data/all_labs_merged.csv"
INDEX_NAME = "embeddings_imgtxt"

#  SigLIP 모델 로드
siglip = UnifiedEmbedder(
    "google/siglip-so400m-patch14-384",
    device="cuda",
    dtype="float16",
    normalize=True
)

# 프레임 로딩 유틸
def read_first_frame(video_path: str, target_w: int = 384, target_h: int = 384) -> Image.Image | None:
    cap = cv2.VideoCapture(video_path)
    ok, frame = cap.read()
    cap.release()
    if not ok or frame is None:
        return None
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return Image.fromarray(frame).resize((target_w, target_h))

def read_n_frames_evenly(
    video_path: str,
    n: int = 10,
    target_w: int = 384,
    target_h: int = 384,
    strict: bool = False
) -> List[Image.Image]:
    imgs: List[Image.Image] = []
    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            return imgs
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total_frames <= 0:
            return imgs
        n_eff = min(n, total_frames)
        idxs = np.linspace(0, total_frames - 1, num=n_eff, dtype=int)
        for idx in idxs:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, frame = cap.read()
            if not ok or frame is None:
                continue
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            imgs.append(Image.fromarray(frame).resize((target_w, target_h)))
    finally:
        cap.release()
    if strict and len(imgs) < n:
        return []
    return imgs

# 임베딩 유틸
def l2_normalize(vec: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    denom = max(float(np.linalg.norm(vec)), eps)
    return vec / denom

def embed_text_with_images_mean(embedder: UnifiedEmbedder, text: str, images: List[Image.Image]) -> np.ndarray:
    if not images:
        raise ValueError("images is empty")
    texts = [text] * len(images)
    embs = embedder.embed_pair_and_fuse(texts, images, mode="mean")  # (N, D)
    embs = np.asarray(embs, dtype=np.float32)
    mean_vec = embs.mean(axis=0)
    return l2_normalize(mean_vec)

# 인덱스 생성(없으면)
def ensure_index(es) -> None:
    try:
        if es.indices.exists(index=INDEX_NAME):
            return
    except Exception:
        # 일부 ES 버전/권한에서 exists가 예외를 던질 수 있음 → 생성 시도
        pass

    mapping = {
        "mappings": {
            "properties": {
                "session_id": {"type": "keyword"},
                "camera_id": {"type": "keyword"},
                "text": {"type": "text"},
                "video_file": {"type": "keyword"},
                "embedding_siglip_fused": {
                    "type": "dense_vector",
                    "dims": 1152,   # SigLIP so400m
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }
    try:
        es.indices.create(index=INDEX_NAME, body=mapping)
        print(f"[INFO] created index {INDEX_NAME}")
    except RequestError as e:
        # 이미 존재 등 경합 시 무시
        if getattr(e, "info", {}).get("error", {}).get("type") != "resource_already_exists_exception":
            print(f"[ERR] index create failed: {e.info}")

# 인덱싱(있으면 스킵)
def embed_and_ingest(n_keyframes: int = 10, skip_existing: bool = True) -> None:
    es = get_client()
    ensure_index(es)

    df = pd.read_csv(CSV_PATH)
    required_cols = {"session_id", "video_summary", "camera_id"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_cols}")

    df_unique = (
        df.dropna(subset=["video_summary"])
          .drop_duplicates(subset=["session_id"])
          [["session_id", "camera_id", "video_summary"]]
    )

    actions = []
    op_type = "create" if skip_existing else "index"  # ✅ create → 존재 시 409로 스킵

    for _, row in df_unique.iterrows():
        session_id = str(row["session_id"])
        camera_id = str(row["camera_id"])
        text = str(row["video_summary"]).strip()
        if not text:
            continue

        video_path = find_video_path(session_id, camera_id)
        if not video_path or not Path(video_path).exists():
            print(f"[SKIP] no video file for {session_id}/{camera_id}")
            continue

        # 10등분 샘플링 → 실패 시 첫 프레임 폴백
        images = read_n_frames_evenly(str(video_path), n=n_keyframes, target_w=384, target_h=384, strict=False)
        if not images:
            img0 = read_first_frame(str(video_path))
            if img0:
                images = [img0]
            else:
                print(f"[SKIP] cannot read frames from {video_path}")
                continue

        try:
            emb_fused_mean = embed_text_with_images_mean(siglip, text, images).tolist()
        except Exception as e:
            print(f"[ERR] session={session_id} embed fail: {e}")
            continue

        actions.append({
            "_op_type": op_type,              # 없을 때만 생성
            "_index": INDEX_NAME,
            "_id": session_id,                # 세션 단위 문서
            "_source": {
                "session_id": session_id,
                "camera_id": camera_id,
                "text": text,
                "video_file": Path(video_path).name,
                "embedding_siglip_fused": emb_fused_mean,
            }
        })

    if not actions:
        print("[INFO] no actions to index")
        return

    success, errors = helpers.bulk(
        es,
        actions,
        raise_on_error=False,   # 409 등 에러 발생해도 계속
        stats_only=False
    )

    # 409(conflict) 스킵 집계
    skipped = 0
    other_errors = 0
    for e in errors:
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
    embed_and_ingest(n_keyframes=10, skip_existing=True)
