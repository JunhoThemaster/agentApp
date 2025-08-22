import numpy as np
from ...es.client import get_client
from ..query_embedder import embed_query

es = get_client()   

# distil 모델로 1차 필터링  
def search_with_distil(query_vec, index="embeddings_text"):
    body = {
        "knn": {
            "field": "embedding_distiluse",   # ✅ ingest 단계와 필드명 맞추기
            "query_vector": query_vec,
            "k": 50,
            "num_candidates": 100
        }
    }
    res = es.search(index=index, body=body)
    return res["hits"]["hits"]

# 조금 더 무겁지만 정확도는 좋은 koe5로 마지막 필터링
def rerank_with_koe5(hits, query_vec):
    rescored = []
    for h in hits:
        doc_vec = np.array(h["_source"]["embedding_koe5"])
        score = np.dot(query_vec, doc_vec) / (
            np.linalg.norm(query_vec) * np.linalg.norm(doc_vec) + 1e-8
        )
        rescored.append((h, score))
    
    rescored.sort(key=lambda x: x[1], reverse=True)
    return rescored[:5]

# 최종 search 함수
def search(q: str, distil_model, koe5_model, index="embeddings_text"):

    q_vec_distil, q_vec_koe5 = embed_query(q, distil_model, koe5_model)
    
    candidates = search_with_distil(q_vec_distil, index=index)
    final_results = rerank_with_koe5(candidates, q_vec_koe5)
    
    return [
        {
            "id": h["_id"],
            "session_id": h["_source"]["session_id"],
            "camera_id": h["_source"].get("camera_id"),   # ✅ 추가
            "video_summary": h["_source"]["text"],
            "score": score
        }
        for h, score in final_results
    ]
