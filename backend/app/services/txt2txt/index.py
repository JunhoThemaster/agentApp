from es.client import es_client

def create_txt2txt_index(index_name: str = "txt2txt_sessions"):
    """
    txt2txt 전용 인덱스 생성
    """
    if not es_client.indices.exists(index=index_name):
        es_client.indices.create(
            index=index_name,
            body={
                "mappings": {
                    "properties": {
                        "session_id": {"type": "keyword"},
                        "video_summary": {"type": "text"},
                        "observation_stats": {"type": "object"},
                        "error_stats": {"type": "object"},
                        "embedding_koe5": {
                            "type": "dense_vector",
                            "dims": 768,
                            "index": True,
                            "similarity": "cosine"
                        },
                        "embedding_distiluse": {
                            "type": "dense_vector",
                            "dims": 512,
                            "index": True,
                            "similarity": "cosine"
                        }
                    }
                }
            }
        )
        print(f"[ES] txt2txt index created: {index_name}")
    else:
        print(f"[ES] Index already exists: {index_name}")
