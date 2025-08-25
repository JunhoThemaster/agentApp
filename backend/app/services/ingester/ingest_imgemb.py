# -*- coding: utf-8 -*-
"""
CSV 기반 SigLIP 텍스트+다중 대표 프레임(균등 샘플링) 멀티모달 임베딩 → Elasticsearch 인덱싱
- video_service.py 의 find_video_path() 활용
"""

import numpy as np
import pandas as pd
from pathlib import Path
from app.es.client import get_client
from elasticsearch import helpers
from elasticsearch.exceptions import NotFoundError, RequestError
from PIL import Image
import cv2
from app.services.env_loader import env_loader
from ...models_emb.embedder_siglip import UnifiedEmbedder
from app.services.video_service import find_video_path  # ✅ 이미 구현한 함수 import


BASE_DIR = env_loader.env_loader()

CSV_PATH = f"{BASE_DIR}/data/all_labs_merged.csv"


INDEX_NAME = "embeddings_imgtxt"

# ✅ SigLIP 모델 로드
siglip = UnifiedEmbedder(
    "google/siglip-so400m-patch14-384",
    device="cuda",
    dtype="float16",
    normalize=True
)

def read_first_frame(video_path: str, target_w=384, target_h=384) -> Image.Image | None:
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
) -> list[Image.Image]:
    imgs: list[Image.Image] = []
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

def l2_normalize(vec: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    denom = max(np.linalg.norm(vec), eps)
    return vec / denom

def embed_text_with_images_mean(embedder: UnifiedEmbedder, text: str, images: list[Image.Image]) -> np.ndarray:
    if not images:
        raise ValueError("images is empty")
    texts = [text] * len(images)
    embs = embedder.embed_pair_and_fuse(texts, images, mode="mean")  # (N, D)
    embs = np.asarray(embs, dtype=np.float32)
    mean_vec = embs.mean(axis=0)
    return l2_normalize(mean_vec)

def create_index(es):
    try:
        es.indices.delete(index=INDEX_NAME)
        print(f"[INFO] 기존 인덱스 {INDEX_NAME} 삭제 완료")
    except NotFoundError:
        print(f"[INFO] 기존 인덱스 {INDEX_NAME} 없음 → 새로 생성 예정")

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
        print(f"[INFO] 새 인덱스 {INDEX_NAME} 생성 완료")
    except RequestError as e:
        print(f"[ERR] 인덱스 생성 실패: {e.info}")

def embed_and_ingest(n_keyframes: int = 10):
    es = get_client()
    create_index(es)

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
            print(f"[ERR] session={session_id} fail: {e}")
            continue

        actions.append({
            "_op_type": "index",
            "_index": INDEX_NAME,
            "_id": session_id,   # session 단위 표현
            "_source": {
                "session_id": session_id,
                "camera_id": camera_id,
                "text": text,
                "video_file": Path(video_path).name,
                "embedding_siglip_fused": emb_fused_mean,
            }
        })

    if actions:
        helpers.bulk(es, actions)
    print(f"[OK] {len(actions)} sessions indexed into {INDEX_NAME}")

if __name__ == "__main__":
    embed_and_ingest(n_keyframes=10)
