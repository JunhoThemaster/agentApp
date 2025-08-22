from sentence_transformers import SentenceTransformer

def load_distil():
    """50개 후보 검색용 (빠른 모델)"""
    return SentenceTransformer("sentence-transformers/distiluse-base-multilingual-cased-v1")

def load_koe5():
    """rerank 용 (정확도 높은 모델)"""
    return SentenceTransformer("nlpai-lab/KoE5")
