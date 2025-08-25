import { useState, useRef, useEffect } from "react";
import { searchTextApi, searchImageApi } from "../api";  // ✅ 텍스트용 / 이미지용 분리

export function useSearchVideos() {
  const [query, setQuery] = useState("");
  const [textResults, setTextResults] = useState<any[]>([]);
  const [imageResults, setImageResults] = useState<any[]>([]);   // ✅ 추가
  const videoRefs = useRef<(HTMLVideoElement | null)[]>([]);

  // 🔎 검색 실행
  const handleSearch = async () => {
    console.log("검색어:", query);

    try {
      const [textRes, imageRes] = await Promise.all([
        fetch(searchTextApi(query)),
        fetch(searchImageApi(query))
      ]);

      if (!textRes.ok || !imageRes.ok) throw new Error("검색 API 오류");

      const textData = await textRes.json();
      const imageData = await imageRes.json();

      setTextResults(textData || []);
      setImageResults(imageData || []);   // ✅ 이미지 결과 반영

      console.log("텍스트 결과:", textData);
      console.log("이미지 결과:", imageData);
    } catch (err) {
      console.error(err);
      setTextResults([]);
      setImageResults([]);
    }
  };

  // 🎬 검색 결과가 바뀔 때마다 자동재생 시도
  useEffect(() => {
    videoRefs.current.forEach((video) => {
      if (video) {
        video.play().catch((err) => {
          console.warn("자동재생 실패:", err);
        });
      }
    });
  }, [textResults]);

  return { query, setQuery, textResults, imageResults, videoRefs, handleSearch };
}
