import os
from pathlib import Path
from dotenv import load_dotenv
from elasticsearch import Elasticsearch

# ------------------------
# 1. 환경 변수 로드
# ------------------------
BASE_DIR = Path(__file__).resolve().parents[1]   # backend/app
load_dotenv(BASE_DIR / ".env")

ES_URL  = os.getenv("ES_URL")
ES_USER = os.getenv("ES_USER")
ES_PASS = os.getenv("ES_PASS")
ES_CA   = os.getenv("ES_CA")

# ------------------------
# 2. Elasticsearch 클라이언트
# ------------------------
es = Elasticsearch(
    [ES_URL],
    basic_auth=(ES_USER, ES_PASS),
    ca_certs=ES_CA,
)

def get_client():
    """Elasticsearch 클라이언트 리턴"""
    return es
