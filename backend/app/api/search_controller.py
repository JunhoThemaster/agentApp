from ..services.txt2txt.search_services import search
from fastapi import APIRouter, Query
from pydantic import BaseModel
from ..services.txt2img.search_servicesImg import search_fused
from ..models_emb import loader
from ..services.video_service import find_video_path


router = APIRouter()

# ---- 모델 로딩 (distil + koe5) ----
distil_model = loader.load_distil()
koe5_model = loader.load_koe5()


class SearchResponse(BaseModel):
    id: str | None = None
    session_id: str
    camera_id : int
    video_summary: str
    score: float
    video_url: str | None = None

# 텍스트 투 텍스트 검색 서비스 호출부 
@router.get("/api/search/text", response_model=list[SearchResponse])
async def search_text(q: str = Query(..., description="검색할 텍스트 쿼리")):
    results = search(q, distil_model, koe5_model)

    enriched_results = []
    for r in results:
        session_id = r["session_id"]
        camera_id  = r["camera_id"]
        video_path = find_video_path(session_id, camera_id)
        print(video_path)
        if video_path:  # 실제 영상이 있는 경우만
            video_url = f"http://localhost:8000/api/video/{session_id}/{camera_id}"
            enriched_results.append(SearchResponse(
                id=r["id"],
                session_id=session_id,
                camera_id=camera_id,
                video_summary=r["video_summary"],
                score=r["score"],
                video_url=video_url
            ))
    print(enriched_results)
    print(len(enriched_results))
    
    return enriched_results

@router.get("/api/search/image", response_model=list[SearchResponse])
async def search_image(q: str = Query(..., description="검색할 이미지 쿼리")):
    results = search_fused(q)  # ✅ SigLIP fused 기반 검색

    enriched_results = []
    for r in results:
        session_id = r["session_id"]
        camera_id  = r["camera_id"]
        video_path = find_video_path(session_id, camera_id)

        if video_path:
            video_url = f"http://localhost:8000/api/video/{session_id}/{camera_id}"
            enriched_results.append(SearchResponse(
                id=r["id"],
                session_id=session_id,
                camera_id=camera_id,
                video_summary=r["text"],
                score=r["score"],
                video_url=video_url
            ))
        print(enriched_results)
    return enriched_results