import React, { useState } from "react";
import "../SearchPage.css";
import { useSearchVideos } from "../hooks/useSearchVideos";

type StatsResponse = {
  session_id: string;
  found: boolean;
  stats: {
    latency?: {
      action_prev?: { mean?: number; std?: number };
      observation_prev?: { mean?: number; std?: number };
    };
    command?: { success_rate?: number };
    tracking_error?: { mean?: number; std?: number };
    joint_velocity_diff?: { mean?: number; std?: number };
  } | null;
};

const SearchPage: React.FC = () => {
  const {
    query,
    setQuery,
    textResults,
    imageResults,
    videoRefs,
    handleSearch,
  } = useSearchVideos();

  // 카드별 통계 데이터/로딩/오류 상태 관리 (session_id 기준)
  const [statsMap, setStatsMap] = useState<Record<string, StatsResponse | null>>({});
  const [openMap, setOpenMap] = useState<Record<string, boolean>>({});
  const [loadingMap, setLoadingMap] = useState<Record<string, boolean>>({});
  const [errorMap, setErrorMap] = useState<Record<string, string | null>>({});

  const fetchStats = async (sessionId: string) => {
    // 이미 불러온 게 있으면 열기/닫기만 토글
    if (statsMap[sessionId]) {
      setOpenMap((m) => ({ ...m, [sessionId]: !m[sessionId] }));
      return;
    }
    try {
      setLoadingMap((m) => ({ ...m, [sessionId]: true }));
      setErrorMap((m) => ({ ...m, [sessionId]: null }));
      const res = await fetch(`http://localhost:8000/api/stats/${encodeURIComponent(sessionId)}`);
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(msg || `HTTP ${res.status}`);
      }
      const data: StatsResponse = await res.json();
      setStatsMap((m) => ({ ...m, [sessionId]: data }));
      setOpenMap((m) => ({ ...m, [sessionId]: true }));
    } catch (e: any) {
      setErrorMap((m) => ({ ...m, [sessionId]: e?.message ?? "에러" }));
    } finally {
      setLoadingMap((m) => ({ ...m, [sessionId]: false }));
    }
  };

  // ===== 포맷팅 유틸 =====
  function fmtNum(x?: number | null, digits = 3) {
    if (x === null || x === undefined || Number.isNaN(x)) return "-";
    return new Intl.NumberFormat("ko-KR", { maximumFractionDigits: digits }).format(x);
  }
  function fmtPercent(x?: number | null) {
    if (x === null || x === undefined || Number.isNaN(x)) return "-";
    return `${new Intl.NumberFormat("ko-KR", { maximumFractionDigits: 1 }).format(x * 100)}%`;
  }
  // latency: 값이 5 미만이면 초로 보고 ms로 변환(예: 0.25 -> 250 ms), 아니면 그대로 ms
  function toMs(x?: number | null) {
    if (x === null || x === undefined || Number.isNaN(x)) return null;
    return x < 5 ? x * 1000 : x;
  }

  // ===== 미니 차트 컴포넌트들 =====

  // 1) 성공률 링 차트 (CSS conic-gradient)
  const MiniRing: React.FC<{ percent?: number | null; size?: number; label?: string }> = ({
    percent,
    size = 48,
    label = "성공률",
  }) => {
    const p = percent ?? 0;
    const pct = Math.max(0, Math.min(100, p * 100));
    const bg = `conic-gradient(#4f46e5 ${pct}%, #e5e7eb ${pct}% 100%)`; // indigo / gray-200
    return (
      <div className="mini-ring" style={{ width: size, height: size, background: bg }}>
        <div className="mini-ring-inner">
          <span className="mini-ring-text">{Math.round(pct)}%</span>
        </div>
        <div className="mini-caption">{label}</div>
      </div>
    );
  };

  // 2) 미니 바(두 값 비교: action vs observation)
  const MiniBars: React.FC<{
    title: string;
    a?: number | null;
    b?: number | null;
    unit?: "ms" | "raw";
    cap?: number; // 스케일 상한 (없으면 자동)
  }> = ({ title, a, b, unit = "ms", cap }) => {
    const av = unit === "ms" ? toMs(a) : a;
    const bv = unit === "ms" ? toMs(b) : b;
    const maxV =
      cap ??
      Math.max(
        1,
        ...( [av ?? 0, bv ?? 0].map((x) => Math.abs(x)) ),
      );
    const aW = av != null ? Math.round((Math.abs(av) / maxV) * 100) : 0;
    const bW = bv != null ? Math.round((Math.abs(bv) / maxV) * 100) : 0;

    return (
      <div className="mini-bars">
        <div className="mini-title">{title}</div>
        <div className="mini-bar-row">
          <span className="mini-bar-label">action</span>
          <div className="mini-bar-track">
            <div className="mini-bar-fill a" style={{ width: `${aW}%` }} />
          </div>
          <span className="mini-bar-val">
            {unit === "ms" ? `${fmtNum(av)} ms` : fmtNum(av)}
          </span>
        </div>
        <div className="mini-bar-row">
          <span className="mini-bar-label">obs</span>
          <div className="mini-bar-track">
            <div className="mini-bar-fill b" style={{ width: `${bW}%` }} />
          </div>
          <span className="mini-bar-val">
            {unit === "ms" ? `${fmtNum(bv)} ms` : fmtNum(bv)}
          </span>
        </div>
      </div>
    );
  };

  // 3) 에러바(평균±표준편차) — 작은 가로 막대
  const MiniErrorBar: React.FC<{
    title: string;
    mean?: number | null;
    std?: number | null;
    cap?: number; // 스케일 상한 (없으면 자동)
  }> = ({ title, mean, std, cap }) => {
    const m = mean ?? 0;
    const s = Math.max(0, std ?? 0);
    const lo = m - s;
    const hi = m + s;
    const maxAbs = cap ?? Math.max(1e-6, Math.abs(m) + s, Math.abs(lo), Math.abs(hi));
    const W = 120; // px
    const centerX = W / 2;
    const scale = centerX / maxAbs; // -maxAbs..+maxAbs → 0..W

    const x0 = Math.max(0, Math.min(W, centerX + lo * scale));
    const x1 = Math.max(0, Math.min(W, centerX + hi * scale));
    const xm = Math.max(0, Math.min(W, centerX + m * scale));

    return (
      <div className="mini-errorbar">
        <div className="mini-title">{title}</div>
        <svg width={W} height={20}>
          {/* 기준선 */}
          <line x1={0} y1={10} x2={W} y2={10} stroke="#e5e7eb" strokeWidth={2} />
          {/* 0점 */}
          <line x1={centerX} y1={5} x2={centerX} y2={15} stroke="#9ca3af" strokeWidth={1} />
          {/* 구간(lo-hi) */}
          <line x1={x0} y1={10} x2={x1} y2={10} stroke="#4f46e5" strokeWidth={4} />
          {/* 평균점 */}
          <circle cx={xm} cy={10} r={3.5} fill="#111827" />
        </svg>
        <div className="mini-meta">
          μ={fmtNum(mean)} / σ={fmtNum(std)}
        </div>
      </div>
    );
  };

  const StatsBlock: React.FC<{ s: StatsResponse | null }> = ({ s }) => {
    if (!s) return null;
    if (!s.found) return <div className="stats-box error">해당 세션 통계가 없습니다.</div>;

    const st = s.stats ?? {};
    const a = st.latency?.action_prev ?? {};
    const o = st.latency?.observation_prev ?? {};
    const te = st.tracking_error ?? {};
    const jv = st.joint_velocity_diff ?? {};

    // latency 스케일 자동 산정(최댓값 기준)
    const msA = toMs(a.mean);
    const msO = toMs(o.mean);
    const msCap = Math.max(100, ...( [msA ?? 0, msO ?? 0] )); // 최소 100ms

    // errorbar 스케일(절대값 기준 자동)
    const errCap = Math.max(
      1e-3,
      Math.abs(te.mean ?? 0) + Math.abs(te.std ?? 0),
      Math.abs(jv.mean ?? 0) + Math.abs(jv.std ?? 0)
    );

    return (
      <div className="stats-box">
        <div className="mini-grid">
          {/* 성공률 링 */}
          <MiniRing percent={st.command?.success_rate ?? null} label="성공률" />

          {/* 지연시간 비교 바 */}
          <MiniBars
            title="지연시간 (평균)"
            a={a.mean}
            b={o.mean}
            unit="ms"
            cap={msCap}
          />

          {/* 트래킹 에러 에러바 */}
          <MiniErrorBar
            title="트래킹 에러 (μ±σ)"
            mean={te.mean}
            std={te.std}
            cap={errCap}
          />

          {/* 조인트 속도차 에러바 */}
          <MiniErrorBar
            title="조인트 속도차 (μ±σ)"
            mean={jv.mean}
            std={jv.std}
            cap={errCap}
          />
        </div>
      </div>
    );
  };

  const renderCard = (result: any, idx: number) => {
    const sid = String(result.session_id);
    const isOpen = !!openMap[sid];
    const isLoading = !!loadingMap[sid];
    const err = errorMap[sid];

    return (
      <div key={sid} className="result-card">
        <p>
          {result.session_id} - {result.camera_id}
        </p>
        <video
          ref={(el) => {
            if (videoRefs.current) videoRefs.current[idx] = el;
          }}
          src={result.video_url}
          controls
          autoPlay
          muted
          width="320"
        />
        <div className="card-actions">
          <button onClick={() => fetchStats(sid)} disabled={isLoading}>
            {isLoading ? "불러오는 중..." : isOpen ? "통계 닫기" : "통계 보기"}
          </button>
        </div>
        {err && <div className="stats-box error">에러: {err}</div>}
        {isOpen && <StatsBlock s={statsMap[sid] ?? null} />}
      </div>
    );
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
        {/* 텍스트 → 텍스트 결과 */}
        <div className="results-column">
          <h2>텍스트 → 텍스트 결과</h2>
          {textResults.slice(0, 5).map((r: any, idx: number) => renderCard(r, idx))}
        </div>

        {/* 텍스트 → 이미지 결과 */}
        <div className="results-column">
          <h2>텍스트 → 이미지 결과</h2>
          {imageResults.slice(0, 5).map((r: any, idx: number) => renderCard(r, idx))}
        </div>
      </div>
    </div>
  );
};

export default SearchPage;
