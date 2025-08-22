import pandas as pd
from es.client import get_client
from elasticsearch import helpers
from sentence_transformers import SentenceTransformer

CSV_PATH = "/home/user2/문서/agentApp/backend/app/data/all_labs_merged.csv"
INDEX_NAME = "embeddings_text"

# ✅ 두 개 모델 로드
koe5 = SentenceTransformer("nlpai-lab/KoE5")
distiluse = SentenceTransformer("sentence-transformers/distiluse-base-multilingual-cased-v1")

def embed_and_ingest():
    es = get_client()
    df = pd.read_csv(CSV_PATH)

    required_cols = {"session_id", "video_summary", "camera_id"}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"CSV must contain columns: {required_cols}")

    # ✅ 세션별 video_summary 하나만 남기기 (세션 단위 중복 제거)
    df_unique = (
        df.dropna(subset=["video_summary"])
          .drop_duplicates(subset=["session_id"])   # 세션 단위로 하나만
          [["session_id", "camera_id", "video_summary"]]
    )

    actions = []
    for _, row in df_unique.iterrows():
        session_id = str(row["session_id"])
        camera_id = str(row["camera_id"])
        text = str(row["video_summary"]).strip()

        if not text:  # ✅ 빈 문자열은 skip
            continue

        emb_koe5 = koe5.encode(text, convert_to_numpy=True).tolist()
        emb_distil = distiluse.encode(text, convert_to_numpy=True).tolist()

        actions.append({
            "_op_type": "index",
            "_index": INDEX_NAME,
            "_id": session_id,  # 세션 단위 유니크
            "_source": {
                "session_id": session_id,
                "camera_id": camera_id,     # ✅ 카메라 ID 추가
                "text": text,
                "embedding_koe5": emb_koe5,
                "embedding_distiluse": emb_distil,
            }
        })

    helpers.bulk(es, actions)
    print(f"[OK] {len(actions)} sessions indexed into {INDEX_NAME}")

if __name__ == "__main__":
    embed_and_ingest()
