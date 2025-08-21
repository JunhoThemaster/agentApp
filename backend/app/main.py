from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from app.api import elastic 
app = FastAPI()

# 현재 파일 기준으로 static 디렉토리 절대 경로 계산
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

# static 디렉토리 존재 확인 후 mount

# 라우터 등록
app.include_router(elastic.router, prefix="/api")

# API 엔드포인트 예시
@app.get("/api/hello")
def read_hello():
    return {"message": "Hello from FastAPI!"}
