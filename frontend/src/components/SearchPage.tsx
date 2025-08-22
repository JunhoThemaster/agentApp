import React, { useState } from "react";
import "../SearchPage.css";
import { searchTextApi, videoStreamApi } from "../api";

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState("");
  const [textResults, setTextResults] = useState<any[]>([]); // 검색 결과 저장

  const handleSearch = async () => {
    console.log("검색어:", query);

    try {
      // 1) 텍스트 검색 API 호출
      const res = await fetch(searchTextApi(query));
      if (!res.ok) throw new Error("검색 API 오류");
      const data = await res.json();

      // ✅ 결과에 videoUrl까지 넣어서 저장
      if (data.results && data.results.length > 0) {
        const enriched = data.results.map((item: any) => ({
          ...item,
          videoUrl: videoStreamApi(item.session_id, item.camera_id),
        }));
        setTextResults(enriched);
      } else {
        setTextResults([]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="search-container">
      {/* 검색 박스 */}
      <div className="search-box">
        <input
          type="text"
          placeholder="검색어를 입력하세요..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button onClick={handleSearch}>검색</button>
      </div>

      {/* 검색 결과 */}
      <div className="results-grid">
        <div className="results-column">
          <h2>텍스트 → 텍스트 결과</h2>
          {textResults.map((item, idx) => (
            <div key={idx} className="result-card">
              <p>{item.text}</p>

              {/* ✅ 결과별 비디오 자동 재생 */}
              {item.videoUrl && (
                <video
                  key={item.videoUrl} // 새 검색 시 강제 리렌더
                  width="320"
                  autoPlay
                  muted
                  loop
                  playsInline
                  controls
                >
                  <source src={item.videoUrl} type="video/mp4" />
                  지원하지 않는 브라우저입니다.
                </video>
              )}
            </div>
          ))}
        </div>

        <div className="results-column">
          <h2>텍스트 → 이미지 결과</h2>
          <div className="result-card">이미지 결과 (추후 연결)</div>
        </div>
      </div>
    </div>
  );
};

export default SearchPage;
