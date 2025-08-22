# -*- coding: utf-8 -*-
"""
CSV 기반 SigLIP 텍스트+첫 프레임 멀티모달 임베딩 → Elasticsearch 인덱싱
- video_service.py 의 find_video_path() 활용
"""

import pandas as pd
from pathlib import Path
from app.es.client import get_client
from elasticsearch import helpers
from elasticsearch.exceptions import NotFoundError, RequestError
from PIL import Image
import cv2

from ...models_emb.embedder_siglip import UnifiedEmbedder
from app.services.video_service import find_video_path  # ✅ 이미 구현한 함수 import

CSV_PATH = "/home/dickson/문서/agentApp/backend/app/data/all_labs_merged.csv"
INDEX_NAME = "embeddings_imgtxt"

# ✅ SigLIP 모델 로드
siglip = UnifiedEmbedder(
    "google/siglip-so400m-patch14-384",
    device="cuda",
    dtype="float16",
    normalize=True
)


def read_first_frame(video_path: str, target_w=384, target_h=384) -> Image.Image:
    """비디오에서 첫 프레임 추출 후 PIL.Image 반환"""
    cap = cv2.VideoCapture(video_path)
    success, frame = cap.read()
    cap.release()
    if not success or frame is None:
        return None
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame).resize((target_w, target_h))
    return img


def create_index(es):
    """ES 인덱스 삭제 후 새 매핑 생성"""
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
                    "dims": 1152,   # ✅ SigLIP so400m 벡터 차원
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


def embed_and_ingest():
    es = get_client()
    create_index(es)   # ✅ 실행할 때마다 인덱스 리셋 & 새 매핑 생성

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

        # ✅ video_service.py에서 경로 찾기
        video_path = find_video_path(session_id, camera_id)
        if not video_path or not Path(video_path).exists():
            print(f"[SKIP] no video file for {session_id}/{camera_id}")
            continue

        # ✅ 첫 프레임 추출
        img = read_first_frame(str(video_path))
        if img is None:
            print(f"[SKIP] cannot read frame from {video_path}")
            continue

        try:
            # 첫 프레임 + 텍스트 → 융합 임베딩
            emb_fused = siglip.embed_pair_and_fuse([text], [img], mode="mean")[0].tolist()
        except Exception as e:
            print(f"[ERR] session={session_id} fail: {e}")
            continue

        actions.append({
            "_op_type": "index",
            "_index": INDEX_NAME,
            "_id": session_id,
            "_source": {
                "session_id": session_id,
                "camera_id": camera_id,
                "text": text,
                "video_file": Path(video_path).name,
                "embedding_siglip_fused": emb_fused,
            }
        })

    if actions:
        helpers.bulk(es, actions)
    print(f"[OK] {len(actions)} sessions indexed into {INDEX_NAME}")


if __name__ == "__main__":
    embed_and_ingest()
