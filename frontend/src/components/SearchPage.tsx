import React from "react";
import "../SearchPage.css";
import { useSearchVideos } from "../hooks/useSearchVideos";

const SearchPage: React.FC = () => {
  const {
    query,
    setQuery,
    textResults,
    imageResults,
    videoRefs,
    handleSearch,
  } = useSearchVideos();

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
        {/* 텍스트 → 텍스트 결과 */}
        <div className="results-column">
          <h2>텍스트 → 텍스트 결과</h2>
          {textResults.slice(0, 5).map((result, idx) => (
            <div key={idx} className="result-card">
              <p>
                {result.session_id} - {result.camera_id}
              </p>
              <video
                ref={(el) => {
                  videoRefs.current[idx] = el;
                }}
                src={result.video_url}
                controls
                autoPlay
                muted
                width="320"
              />
            </div>
          ))}
        </div>

        {/* 텍스트 → 이미지 결과 */}
        <div className="results-column">
          <h2>텍스트 → 이미지 결과</h2>
          {imageResults.slice(0, 5).map((result, idx) => (
            <div key={idx} className="result-card">
              <p>
                {result.session_id} - {result.camera_id}
              </p>
              <video
                src={result.video_url}
                controls
                autoPlay
                muted
                width="320"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default SearchPage;
