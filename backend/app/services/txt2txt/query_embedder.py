def embed_query(query: str, distil_model, koe5_model):
    """
    문자열 쿼리를 임베딩 벡터 2개로 변환
    - distil_model: 50개 후보 검색용
    - koe5_model:   rerank (top-5)용
    """
    q_vec_distil = distil_model.encode(query, normalize_embeddings=True)
    q_vec_koe5   = koe5_model.encode(query, normalize_embeddings=True)
    return q_vec_distil, q_vec_koe5
