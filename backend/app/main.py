from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
from app.api import search_controller,video_controller,stats_controller
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

# 현재 파일 기준으로 static 디렉토리 절대 경로 계산
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 단계에서는 전체 허용 (배포 시 특정 도메인만)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# static 디렉토리 존재 확인 후 mount
app.include_router(search_controller.router)
app.include_router(video_controller.router)
app.include_router(stats_controller.router)
# 라우터 등록

# API 엔드포인트 예시
@app.get("/api/hello")
def read_hello():
    return {"message": "Hello from FastAPI!"}
