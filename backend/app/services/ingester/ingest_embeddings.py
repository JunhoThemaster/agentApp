import pandas as pd
from elasticsearch import helpers
from elasticsearch.exceptions import RequestError
from sentence_transformers import SentenceTransformer
from app.es.client import get_client
from app.services.env_loader import env_loader

# 설정
BASE_DIR = env_loader.env_loader() 
CSV_PATH = f"{BASE_DIR}/data/all_labs_merged.csv"
INDEX_NAME = "embeddings_text"

#  모델 로드
koe5 = SentenceTransformer("nlpai-lab/KoE5")
distiluse = SentenceTransformer("sentence-transformers/distiluse-base-multilingual-cased-v1")

# 각 모델 차원
DIM_KOE5 = koe5.get_sentence_embedding_dimension()      #  768
DIM_DISTIL = distiluse.get_sentence_embedding_dimension()  #  512


# 인덱스 생성(없으면)
def ensure_index(es):
    try:
        if es.indices.exists(index=INDEX_NAME):
            return
    except Exception:
        pass

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
    try:
        es.indices.create(index=INDEX_NAME, body=mapping)
        print(f"[INFO] created index {INDEX_NAME}")
    except RequestError as e:
        if getattr(e, "info", {}).get("error", {}).get("type") != "resource_already_exists_exception":
            print(f"[ERR] index create failed: {e.info}")


# 임베딩 + 인덱싱(있으면 스킵)
def embed_and_ingest(skip_existing: bool = True):
    es = get_client()
    ensure_index(es)

    df = pd.read_csv(CSV_PATH)

    required_cols = {"session_id", "video_summary", "camera_id"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_cols}")

    df_unique = (
        df.dropna(subset=["video_summary"])
          .drop_duplicates(subset=["session_id"])  # 세션당 1개만
          [["session_id", "camera_id", "video_summary"]]
    )

    actions = []
    op_type = "create" if skip_existing else "index" 

    for _, row in df_unique.iterrows():
        session_id = str(row["session_id"])
        camera_id = str(row["camera_id"])
        text = str(row["video_summary"]).strip()
        if not text:
            continue

        emb_koe5 = koe5.encode(text, convert_to_numpy=True).tolist()
        emb_distil = distiluse.encode(text, convert_to_numpy=True).tolist()

        actions.append({
            "_op_type": op_type,
            "_index": INDEX_NAME,
            "_id": session_id,  # 세션 단위 문서. 카메라별로 구분하려면 f"{session_id}:{camera_id}" 사용
            "_source": {
                "session_id": session_id,
                "camera_id": camera_id,
                "text": text,
                "embedding_koe5": emb_koe5,
                "embedding_distiluse": emb_distil,
            }
        })

    if not actions:
        print("[INFO] no actions to index")
        return

    success, errors = helpers.bulk(
        es, actions, raise_on_error=False, stats_only=False
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
    embed_and_ingest(skip_existing=True)
