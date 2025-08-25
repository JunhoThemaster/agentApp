import pandas as pd
from app.es.client import get_client
from elasticsearch import helpers
from sentence_transformers import SentenceTransformer
from app.services.env_loader import env_loader

BASE_DIR = env_loader.env_loader()


CSV_PATH = f"{BASE_DIR}/data/all_labs_merged.csv"
INDEX_NAME = "embeddings_text"

# ✅ 모델 로드
koe5 = SentenceTransformer("nlpai-lab/KoE5")
distiluse = SentenceTransformer("sentence-transformers/distiluse-base-multilingual-cased-v1")

# ✅ 각 모델 차원 확인 (KoE5=768, Distiluse=512 보통 고정)
DIM_KOE5 = koe5.get_sentence_embedding_dimension()
DIM_DISTIL = distiluse.get_sentence_embedding_dimension()

def create_index(es):
    """
    기존 인덱스 삭제 후 새 매핑으로 생성
    """
    if es.indices.exists(index=INDEX_NAME):
        es.indices.delete(index=INDEX_NAME)
        print(f"[INFO] Deleted existing index: {INDEX_NAME}")

    mapping = {
        "mappings": {
            "properties": {
                "session_id": {"type": "keyword"},
                "camera_id": {"type": "keyword"},
                "text": {"type": "text"},
                "embedding_koe5": {
                    "type": "dense_vector",
                    "dims": DIM_KOE5,
                    "index": True,
                    "similarity": "cosine"
                },
                "embedding_distiluse": {
                    "type": "dense_vector",
                    "dims": DIM_DISTIL,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    es.indices.create(index=INDEX_NAME, body=mapping)
    print(f"[INFO] Created index: {INDEX_NAME} with mapping")

def embed_and_ingest():
    es = get_client()
    create_index(es)  # ✅ 인덱스 매핑 자동 생성

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

        emb_koe5 = koe5.encode(text, convert_to_numpy=True).tolist()
        emb_distil = distiluse.encode(text, convert_to_numpy=True).tolist()

        actions.append({
            "_op_type": "index",
            "_index": INDEX_NAME,
            "_id": session_id,
            "_source": {
                "session_id": session_id,
                "camera_id": camera_id,
                "text": text,
                "embedding_koe5": emb_koe5,
                "embedding_distiluse": emb_distil,
            }
        })

    helpers.bulk(es, actions)
    print(f"[OK] {len(actions)} sessions indexed into {INDEX_NAME}")

if __name__ == "__main__":
    embed_and_ingest()
