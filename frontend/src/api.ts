// src/api.ts
const API_BASE_URL = "http://localhost:8000"; // ✅ 나중에 env로 분리 가능

// --- 텍스트 → 텍스트 검색 API ---
export const searchTextApi = (query: string) => {
  return `${API_BASE_URL}/api/search/text?q=${encodeURIComponent(query)}`;
};

// --- 텍스트 → 이미지 검색 API ---
export const searchImageApi = (query: string) => {
  return `${API_BASE_URL}/api/search/image?q=${encodeURIComponent(query)}`;
};

// --- 비디오 스트리밍 API ---
export const videoStreamApi = (sessionId: string, cameraId: string) => {
  return `${API_BASE_URL}/api/video/${sessionId}/${cameraId}`;
};
