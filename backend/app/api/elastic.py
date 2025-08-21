from fastapi import APIRouter
from elasticsearch import Elasticsearch

router = APIRouter()

# Elasticsearch 연결
es = Elasticsearch(
    "https://localhost:9200",
    ca_certs="/home/dickson/http_ca.crt",   # 사용자 홈에 복사한 인증서
    basic_auth=("elastic", "")  # 초기 비밀번호
)

@router.get("/es")
def es_info():
    """클러스터 정보 확인"""
    return es.info()

@router.post("/es/add")
def add_doc(index: str, doc_id: str, content: dict):
    """문서 추가"""
    return es.index(index=index, id=doc_id, document=content)

@router.get("/es/get")
def get_doc(index: str, doc_id: str):
    """문서 조회"""
    return es.get(index=index, id=doc_id)
