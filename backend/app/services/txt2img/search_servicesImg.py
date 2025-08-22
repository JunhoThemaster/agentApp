import numpy as np
from ...es.client import get_client
from ..query_embedder import embed_query_fused   # ✅ SigLIP fused 전용
from ...models_emb.embedder_siglip import UnifiedEmbedder
es = get_client()

# fused 벡터 기반 KNN 검색
def search_with_fused(query_vec, index="embeddings_imgtxt"):
    body = {
        "knn": {
            "field": "embedding_siglip_fused",   # ✅ ingest 단계와 맞춤
            "query_vector": query_vec,
            "k": 50,             # 후보는 넉넉히 뽑고
            "num_candidates": 100
        }
    }
    res = es.search(index=index, body=body)
    return res["hits"]["hits"]


siglip = UnifiedEmbedder(
    "google/siglip-so400m-patch14-384",
    device="cuda",
    dtype="float16",
    normalize=True
)



# 최종 search 함수 (상위 5개만 반환)
def search_fused(q: str, index="embeddings_imgtxt"):

    # ✅ 쿼리 임베딩 (인스턴스 siglip 사용!)
    q_vec = embed_query_fused(q, siglip)

    # 후보 검색
    candidates = search_with_fused(q_vec, index=index)

    # 상위 5개만 추려서 반환
    return [
        {
            "id": h["_id"],
            "session_id": h["_source"]["session_id"],
            "camera_id": h["_source"].get("camera_id"),
            "video_file": h["_source"].get("video_file"),
            "text": h["_source"].get("text"),
            "score": h["_score"],   # ES에서 계산된 유사도 점수
        }
        for h in candidates[:5]
    ]
