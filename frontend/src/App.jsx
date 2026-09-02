import { useState, useEffect } from "react";
import "./App.css";

function App() {
  // Navigation & UI Configuration
  const [activeTab, setActiveTab] = useState("dashboard");
  const [auditType, setAuditType] = useState("page"); // "page" or "site"
  const [theme, setTheme] = useState(() => {
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem("theme");
      if (saved) return saved;
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    return "light";
  });

  // Data States
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [siteResult, setSiteResult] = useState(null);
  const [selectedSitePageResult, setSelectedSitePageResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(false);
  const [error, setError] = useState("");

  const API = import.meta.env.VITE_API_URL || "";

  // Apply Theme class to document element
  useEffect(() => {
    if (theme === "dark") {
      document.documentElement.classList.add("dark");
      document.documentElement.classList.remove("light");
    } else {
      document.documentElement.classList.add("light");
      document.documentElement.classList.remove("dark");
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
    localStorage.setItem("theme", theme === "light" ? "dark" : "light");
  };

  // =========================================================
  // ANALYZE WEBSITE (triggers crawl)
  // =========================================================

  const analyzeWebsite = async () => {
    if (!url.trim()) {
      setError("Please enter a website URL.");
      return;
    }

    let targetUrl = url.trim();

    if (
      !targetUrl.startsWith("http://") &&
      !targetUrl.startsWith("https://")
    ) {
      targetUrl = `https://${targetUrl}`;
    }

    setLoading(true);
    setError("");
    setResult(null);
    setSiteResult(null);
    setSelectedSitePageResult(null);

    try {
      const endpoint =
        auditType === "site"
          ? `${API}/site-crawl`
          : `${API}/crawl`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: targetUrl,
        }),
      });

      let data = null;

      try {
        data = await response.json();
      } catch {
        data = null;
      }

      console.log("BACKEND STATUS:", response.status);
      console.log("BACKEND DATA:", data);

      if (!response.ok) {
        throw new Error(
          data?.detail ||
          `SearchPilot returned an error (${response.status}).`
        );
      }

      if (auditType === "site") {
        setSiteResult(data);
        setActiveTab("site");
        const averageScore = Math.round(Number(data?.average_score) || 0);
        const grade =
          averageScore >= 90
            ? "Excellent"
            : averageScore >= 75
              ? "Good"
              : averageScore >= 50
                ? "Needs Improvement"
                : "Poor";
        setAuditHistory((prev) => [
          {
            id: Date.now(),
            url: targetUrl,
            type: "site",
            score: averageScore,
            grade,
            pages: data?.pages_crawled || 0,
            data,
            timestamp: new Date().toISOString(),
          },
          ...prev,
        ].slice(0, 10));
      } else {
        setResult(data);
        setActiveTab("page");
        const score = Number(data?.seo_analysis?.score) || 0;
        setAuditHistory((prev) => [
          {
            id: Date.now(),
            url: targetUrl,
            type: "page",
            score,
            grade: data?.seo_analysis?.grade || "Unknown",
            data,
            timestamp: new Date().toISOString(),
          },
          ...prev,
        ].slice(0, 10));
      }
    } catch (err) {
      console.error("SEARCHPILOT ERROR:", err);

      if (err instanceof TypeError) {
        setError(
          "Could not reach the SearchPilot backend. Make sure FastAPI is running on port 8000."
        );
      } else {
        setError(
          err.message ||
          "The website could not be analyzed."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // OPEN SITE PAGE AUDIT (Drill down)
  // =========================================================

  const openSitePageAudit = async (pageUrl) => {
    setPageLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/crawl`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          url: pageUrl,
        }),
      });

      let data = null;

      try {
        data = await response.json();
      } catch {
        data = null;
      }

      if (!response.ok) {
        throw new Error(
          data?.detail ||
          "Could not analyze this page."
        );
      }

      setSelectedSitePageResult(data);

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    } catch (err) {
      console.error("SITE PAGE AUDIT ERROR:", err);

      setError(
        err.message ||
        "Could not analyze the selected page."
      );
    } finally {
      setPageLoading(false);
    }
  };

  // =========================================================
  // RESET
  // =========================================================

  const resetAnalysis = () => {
    setResult(null);
    setSiteResult(null);
    setSelectedSitePageResult(null);
    setUrl("");
    setError("");
    setActiveTab("dashboard");
  };

  // =========================================================
  // PAGE DATA (Page Audit report variables)
  // =========================================================

  const activePageResult = activeTab === "page" ? result : selectedSitePageResult;
  const seo = activePageResult?.seo_analysis;
  const crawl = activePageResult?.crawl;

  const keywordAnalysis =
    seo?.keyword_analysis || [];

  const opportunities =
    seo?.keyword_opportunities || [];

  const keywords =
    crawl?.content?.keywords || [];

  const openGraph =
    crawl?.seo?.open_graph || {};

  const scoreClass =
    seo?.score >= 90
      ? "excellent"
      : seo?.score >= 75
        ? "good"
        : seo?.score >= 50
          ? "needs-improvement"
          : "poor";

  // =========================================================
  // SITE DATA (Full Site Audit report variables)
  // =========================================================

  const sitePages = (
    siteResult?.pages || []
  ).filter(
    (page) =>
      typeof page.score === "number" || page.grade === "Failed"
  );

  const siteScores =
    sitePages
      .filter((page) => page.grade !== "Failed")
      .map((page) => page.score);

  const averageScore =
    siteScores.length > 0
      ? Number(
        siteResult?.average_score ??
        siteScores.reduce(
          (sum, score) =>
            sum + score,
          0
        ) / siteScores.length
      )
      : 0;

  const highestScore =
    siteScores.length > 0
      ? Math.max(...siteScores)
      : 0;

  const lowestScore =
    siteScores.length > 0
      ? Math.min(...siteScores)
      : 0;

  const goodPages =
    sitePages.filter(
      (page) =>
        page.grade !== "Failed" && page.score >= 75
    ).length;

  const needsAttention =
    sitePages.filter(
      (page) =>
        page.grade === "Failed" || page.score < 75
    ).length;

  const excellentPages =
    sitePages.filter(
      (page) =>
        page.grade !== "Failed" && page.score >= 90
    ).length;

  const issueFreePages =
    sitePages.filter(
      (page) =>
        page.grade !== "Failed" && Number(page.issues || 0) === 0
    ).length;

  const pagesWithIssues =
    sitePages.filter(
      (page) =>
        page.grade === "Failed" || Number(page.issues || 0) > 0
    ).length;

  const averageIssues =
    sitePages.length > 0
      ? (
        sitePages.reduce(
          (sum, page) =>
            sum +
            Number(
              page.issues || 0
            ),
          0
        ) /
        sitePages.length
      ).toFixed(1)
      : 0;

  const bestPage =
    siteScores.length > 0
      ? sitePages
        .filter((page) => page.grade !== "Failed")
        .reduce((best, page) =>
          page.score > best.score ? page : best
        )
      : null;

  const worstPage =
    sitePages.length > 0
      ? sitePages.reduce((worst, page) => {
        if (worst.grade === "Failed") return worst;
        if (page.grade === "Failed") return page;
        return page.score < worst.score ? page : worst;
      })
      : null;

  const scoreBuckets = [
    {
      label: "Excellent",
      range: "90–100",
      count: sitePages.filter(
        (page) =>
          page.grade !== "Failed" && page.score >= 90
      ).length,
      className: "excellent",
    },
    {
      label: "Good",
      range: "75–89",
      count: sitePages.filter(
        (page) =>
          page.grade !== "Failed" && page.score >= 75 && page.score < 90
      ).length,
      className: "good",
    },
    {
      label: "Needs Improvement",
      range: "50–74",
      count: sitePages.filter(
        (page) =>
          page.grade !== "Failed" && page.score >= 50 && page.score < 75
      ).length,
      className: "needs-improvement",
    },
    {
      label: "Poor",
      range: "0–49",
      count: sitePages.filter(
        (page) =>
          page.grade === "Failed" || page.score < 50
      ).length,
      className: "poor",
    },
  ];

  const siteScoreClass =
    averageScore >= 90
      ? "excellent"
      : averageScore >= 75
        ? "good"
        : averageScore >= 50
          ? "needs-improvement"
          : "poor";

  // =========================================================
  // RENDER APPSHELL & DASHBOARD
  // =========================================================

  return (
    <div className="app">
      {/* SaaS HEADER */}
      <header className="app-header">
        <div className="logo-group">
          <span className="logo-icon">▲</span>
          <span className="logo-text">SearchPilot</span>
          <span className="logo-badge">Beta</span>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-btn ${activeTab === "dashboard" ? "active" : ""}`}
            onClick={() => handleNavClick("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={`nav-btn ${activeTab === "page" ? "active" : ""}`}
            onClick={() => handleNavClick("page")}
          >
            Page Audit
          </button>
          <button
            className={`nav-btn ${activeTab === "site" ? "active" : ""}`}
            onClick={() => handleNavClick("site")}
          >
            Site Audit
          </button>
        </nav>

        <div className="header-actions">
          <button
            className="theme-btn"
            onClick={toggleTheme}
            title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
          >
            {theme === "light" ? "🌙" : "☀️"}
          </button>
          <div className="user-profile-badge" title="Developer Profile">
            SP
          </div>
        </div>
      </header>

      {/* MAIN CONTAINER */}
      <div className="container">
        {/* Loader Overlay for full-site audits */}
        {pageLoading && (
          <div className="loading-overlay-saas">
            <div className="saas-spinner"></div>
            <p>Analyzing selected page details...</p>
          </div>
        )}

        {/* Global Loading View */}
        {loading && (
          <div className="loading-container-saas">
            <div className="saas-spinner"></div>
            <h3>Analyzing {url}</h3>
            <p className="loading-subtitle">
              {auditType === "site"
                ? "Crawling pages and calculating technical SEO scores..."
                : "Fetching webpage content and evaluating SEO checklist..."}
            </p>
          </div>
        )}

        {/* Global Error Banner */}
        {!loading && error && (
          <div className="error-banner-saas">
            <div className="error-title-saas">Unable to analyze this website</div>
            <p className="error-desc-saas">{error}</p>
            <p className="error-action-saas">
              Try another URL or check that the server is publicly accessible and correct.
            </p>
          </div>
        )}

        {/* =====================================================
            TAB 1: DASHBOARD (HOME SEARCH)
            ====================================================== */}
        {!loading && activeTab === "dashboard" && (
          <div className="dashboard-layout">
            <div className="search-section">
              <div className="search-title-group">
                <h2>SearchPilot</h2>
                <p>Technical SEO intelligence for your website.</p>
              </div>

              <div className="search-box-saas">
                <input
                  type="text"
                  placeholder="https://example.com"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      analyzeWebsite();
                    }
                  }}
                />
                <button onClick={analyzeWebsite} disabled={loading}>
                  Analyze
                </button>
              </div>

              <div className="segmented-control-wrapper">
                <div className="segmented-control">
                  <button
                    className={auditType === "page" ? "active" : ""}
                    onClick={() => setAuditType("page")}
                  >
                    Page Audit
                  </button>
                  <button
                    className={auditType === "site" ? "active" : ""}
                    onClick={() => setAuditType("site")}
                  >
                    Full Site Audit
                  </button>
                </div>
              </div>
            </div>

            {/* Empty state welcome card */}
            <div className="empty-state-saas">
              <div className="empty-state-icon">🔎</div>
              <h3>No audit loaded</h3>
              <p>
                Enter a website URL above and select the audit depth to begin generating SEO score cards.
              </p>
            </div>
          </div>
        )}

        {/* =====================================================
            TAB 2: PAGE AUDIT REPORT
            ====================================================== */}
        {!loading && activeTab === "page" && (
          <>
            {seo ? (
              <div className="results">
                {/* Header */}
                <div className="report-header-saas">
                  <div className="report-title-col">
                    <span className="report-type-badge">Page Audit</span>
                    <h2>{crawl?.seo?.title?.value || "Page Analysis"}</h2>
                    <a
                      href={crawl?.url || url}
                      target="_blank"
                      rel="noreferrer"
                      className="report-anchor"
                    >
                      {crawl?.url || url}
                    </a>
                  </div>
                  <div className="report-actions">
                    <button className="new-analysis" onClick={resetAnalysis}>
                      New Analysis
                    </button>
                  </div>
                </div>

                {/* SaaS Score Card */}
                <div className="score-card-saas">
                  <div className="score-main-col">
                    <span className="score-label-text">Overall SEO Score</span>
                    <div className="score-value-row">
                      <span className="score-value-num">{seo.score}</span>
                      <span className="score-value-slash">/100</span>
                      <span className={`score-value-grade ${scoreClass}`}>{seo.grade}</span>
                    </div>
                    <div className="score-bar-bg">
                      <div className={`score-bar-fill ${scoreClass}`} style={{ width: `${seo.score}%` }}></div>
                    </div>
                  </div>

                  <div className="score-metrics-col">
                    <div className="score-metric-item">
                      <span className="sm-label">Total Issues</span>
                      <span className="sm-value error">{seo.issues?.length || 0}</span>
                    </div>
                    <div className="score-metric-item">
                      <span className="sm-label">Passed Checks</span>
                      <span className="sm-value success">{seo.passed?.length || 0}</span>
                    </div>
                    <div className="score-metric-item">
                      <span className="sm-label">Internal Links</span>
                      <span className="sm-value">{crawl?.links?.internal ?? 0}</span>
                    </div>
                    <div className="score-metric-item">
                      <span className="sm-label">External Links</span>
                      <span className="sm-value">{crawl?.links?.external ?? 0}</span>
                    </div>
                  </div>
                </div>

                {/* Section: Page Information */}
                <section className="section-saas">
                  <div className="section-header-saas">
                    <h3>Page Information</h3>
                    <span>On-Page Data</span>
                  </div>
                  <div className="saas-table-wrapper">
                    <table className="saas-table compact">
                      <tbody>
                        <tr>
                          <td className="property-name-cell">Page Title</td>
                          <td className="property-value-cell bold-text">
                            {crawl?.seo?.title?.value || <span className="empty-val">Missing</span>}
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">Meta Description</td>
                          <td className="property-value-cell">
                            {crawl?.seo?.meta_description?.value || <span className="empty-val">Missing</span>}
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">Canonical URL</td>
                          <td className="property-value-cell">
                            {crawl?.seo?.canonical || <span className="empty-val">Missing</span>}
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">Primary H1 Heading</td>
                          <td className="property-value-cell">
                            {crawl?.seo?.h1?.values?.[0] || <span className="empty-val">No H1 heading found</span>}
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">H2 Count</td>
                          <td className="property-value-cell">
                            {crawl?.content?.headings?.h2?.length ?? 0}
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">Word Count</td>
                          <td className="property-value-cell">
                            {crawl?.content?.word_count ?? 0} words
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">Images (Total)</td>
                          <td className="property-value-cell">
                            {crawl?.seo?.images?.total ?? 0}
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">Images Missing Alt Text</td>
                          <td className="property-value-cell">
                            {crawl?.seo?.images?.missing_alt ?? 0}
                          </td>
                        </tr>
                        <tr>
                          <td className="property-name-cell">Security Protocol</td>
                          <td className="property-value-cell">
                            {crawl?.url?.startsWith("https://") ? (
                              <span className="badge-saas success">HTTPS Secured</span>
                            ) : (
                              <span className="empty-val">HTTP (Unsecured)</span>
                            )}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </section>

                {/* Section: Technical SEO */}
                <section className="section-saas">
                  <div className="section-header-saas">
                    <h3>Technical SEO</h3>
                    <span>Technical Metadata</span>
                  </div>
                  <div className="tech-seo-grid-saas">
                    <div className="tech-seo-card-saas">
                      <span className="tech-card-label">Robots Meta Directive</span>
                      <span className="tech-card-value">{crawl?.seo?.robots || "Not specified"}</span>
                    </div>
                    <div className="tech-seo-card-saas">
                      <span className="tech-card-label">Robots.txt File</span>
                      <span className={`tech-card-value ${crawl?.seo?.robots_txt?.exists ? "success" : "error"}`}>
                        {crawl?.seo?.robots_txt?.exists ? "Found / Accessible" : "Not Found"}
                      </span>
                    </div>
                    <div className="tech-seo-card-saas">
                      <span className="tech-card-label">XML Sitemap</span>
                      <span className={`tech-card-value ${crawl?.seo?.sitemap?.exists ? "success" : "error"}`}>
                        {crawl?.seo?.sitemap?.exists ? "Found / Accessible" : "Not Found"}
                      </span>
                    </div>
                    <div className="tech-seo-card-saas">
                      <span className="tech-card-label">Mobile Viewport configuration</span>
                      <span className="tech-card-value">{crawl?.seo?.viewport ? "Configured" : "Missing"}</span>
                    </div>
                    <div className="tech-seo-card-saas">
                      <span className="tech-card-label">Open Graph Data</span>
                      <span className="tech-card-value">
                        {Object.keys(openGraph).length > 0 ? "Present" : "Missing"}
                      </span>
                    </div>
                    <div className="tech-seo-card-saas">
                      <span className="tech-card-label">Structured Schema Data</span>
                      <span className="tech-card-value">
                        {crawl?.seo?.structured_data?.exists
                          ? `${crawl.seo.structured_data.count} Schema Markups`
                          : "Missing"}
                      </span>
                    </div>
                  </div>
                </section>

                {/* Section: Keyword Analysis */}
                <section className="section-saas">
                  <div className="section-header-saas">
                    <h3>Keyword Analysis</h3>
                    <span>Density & SEO Placement</span>
                  </div>
                  {keywordAnalysis.length > 0 ? (
                    <div className="saas-table-wrapper">
                      <table className="saas-table">
                        <thead>
                          <tr>
                            <th>Keyword / Phrase</th>
                            <th>Count</th>
                            <th>Density</th>
                            <th>In Title</th>
                            <th>In H1</th>
                            <th>In Meta Description</th>
                          </tr>
                        </thead>
                        <tbody>
                          {keywordAnalysis.map((item, index) => (
                            <tr key={`${item.keyword}-${index}`}>
                              <td className="kw-text">{item.keyword}</td>
                              <td>{item.count}</td>
                              <td>{item.density}%</td>
                              <td>
                                {item.in_title ? (
                                  <span className="badge-saas success">✓</span>
                                ) : (
                                  <span className="badge-saas secondary">—</span>
                                )}
                              </td>
                              <td>
                                {item.in_h1 ? (
                                  <span className="badge-saas success">✓</span>
                                ) : (
                                  <span className="badge-saas secondary">—</span>
                                )}
                              </td>
                              <td>
                                {item.in_meta_description ? (
                                  <span className="badge-saas success">✓</span>
                                ) : (
                                  <span className="badge-saas secondary">—</span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : keywords.length > 0 ? (
                    <div className="saas-table-wrapper">
                      <table className="saas-table">
                        <thead>
                          <tr>
                            <th>Keyword</th>
                            <th>Count</th>
                            <th>Density</th>
                          </tr>
                        </thead>
                        <tbody>
                          {keywords.map((item, index) => (
                            <tr key={`${item.keyword}-${index}`}>
                              <td className="kw-text">{item.keyword}</td>
                              <td>{item.count}</td>
                              <td>{item.density}%</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="empty-state-saas">
                      <h3>No keywords found</h3>
                    </div>
                  )}
                </section>

                {/* Section: Keyword Opportunities */}
                <section className="section-saas">
                  <div className="section-header-saas">
                    <h3>Keyword Opportunities</h3>
                    <span>Missing Elements Recommendations</span>
                  </div>
                  {opportunities.length > 0 ? (
                    <div className="opportunities-grid-saas">
                      {opportunities.map((item, index) => {
                        const placements = [];
                        if (!item.in_title) placements.push("Title");
                        if (!item.in_h1) placements.push("H1");
                        if (!item.in_meta_description) placements.push("Meta Description");

                        return (
                          <div className="opp-row-saas" key={`${item.keyword}-${index}`}>
                            <div className="opp-keyword-col">
                              <span className="opp-kw-text">{item.keyword}</span>
                              <span className="opp-usage-text">
                                Used {item.count} times ({item.density}% density)
                              </span>
                            </div>
                            <div className="opp-content-col">
                              <span className="opp-placement-label">
                                Missing from: {placements.join(", ")}
                              </span>
                              <p className="opp-rec-text">
                                Consider naturally incorporating this high-frequency keyword into the missing
                                SEO tags to increase organic search performance.
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="empty-state-saas">
                      <h3>No obvious opportunities found</h3>
                      <p>Your keywords are already well incorporated into important structural elements.</p>
                    </div>
                  )}
                </section>

                {/* Section: Issues list */}
                <section className="section-saas">
                  <div className="section-header-saas">
                    <h3>Technical & Content Issues</h3>
                    <span>Prioritized Checklist</span>
                  </div>
                  {seo.issues?.length > 0 ? (
                    <div className="issues-container-saas">
                      {seo.issues.map((issue, index) => (
                        <div className="issue-row-saas" key={`${issue.category}-${index}`}>
                          <div className="issue-severity-col">
                            <span className={`indicator-dot-saas ${issue.type}`}></span>
                            <span className={`severity-label-saas ${issue.type}`}>{issue.type}</span>
                          </div>
                          <div className="issue-content-col">
                            <span className="issue-category-label">{issue.category}</span>
                            <p className="issue-message-text">{issue.message}</p>
                            {issue.recommendation && (
                              <div className="issue-rec-block">
                                <strong>Recommendation:</strong> {issue.recommendation}
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state-saas">
                      <h3>No issues detected</h3>
                      <p>Your page compiles perfectly with our technical and structured SEO requirements.</p>
                    </div>
                  )}
                </section>

                {/* Section: Passed Checks */}
                <section className="section-saas">
                  <div className="section-header-saas">
                    <h3>Passed Checks</h3>
                    <span>Successful Checklist Matches</span>
                  </div>
                  {seo.passed?.length > 0 ? (
                    <div className="passed-grid-saas">
                      {seo.passed.map((item, index) => (
                        <div className="passed-item-saas" key={`${item}-${index}`}>
                          <span className="passed-icon-saas">✓</span>
                          <span className="passed-text-saas">{item}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state-saas">
                      <h3>No checks passed</h3>
                    </div>
                  )}
                </section>
              </div>
            ) : (
              <div className="empty-state-saas">
                <div className="empty-state-icon">📄</div>
                <span className="report-type-badge">PAGE AUDIT</span>
                <h3>Analyze a webpage</h3>
                <p>Enter a URL below to run a detailed SEO audit.</p>
                <div className="search-box-saas" style={{maxWidth: "680px", margin: "24px auto 0"}}>
                  <input
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com"
                  />
                  <button
                    onClick={() => {
                      setAuditType("page");
                      analyzeWebsite();
                    }}
                    disabled={loading || !url.trim()}
                  >
                    {loading ? "Analyzing..." : "Analyze Page"}
                  </button>
                </div>
              </div>
            )}
          </>
        )}

        {/* =====================================================
            TAB 3: FULL SITE AUDIT REPORT
            ====================================================== */}
        {!loading && activeTab === "site" && (
          <>
            {siteResult ? (
              selectedSitePageResult ? (
                // Drill-down detailed Page Audit inside Site Audit Context
                <div className="results">
                  <div style={{ marginBottom: "20px" }}>
                    <button
                      className="new-analysis"
                      onClick={() => {
                        setSelectedSitePageResult(null);
                        setError("");
                      }}
                    >
                      ← Back to Site Overview
                    </button>
                  </div>

                  <div className="report-header-saas">
                    <div className="report-title-col">
                      <span className="report-type-badge">Site Audit / Page Details</span>
                      <h2>{crawl?.seo?.title?.value || "Page Analysis"}</h2>
                      <span className="report-anchor">{crawl?.url || url}</span>
                    </div>
                  </div>

                  {/* SaaS Score Card */}
                  <div className="score-card-saas">
                    <div className="score-main-col">
                      <span className="score-label-text">Overall SEO Score</span>
                      <div className="score-value-row">
                        <span className="score-value-num">{seo.score}</span>
                        <span className="score-value-slash">/100</span>
                        <span className={`score-value-grade ${scoreClass}`}>{seo.grade}</span>
                      </div>
                      <div className="score-bar-bg">
                        <div className={`score-bar-fill ${scoreClass}`} style={{ width: `${seo.score}%` }}></div>
                      </div>
                    </div>

                    <div className="score-metrics-col">
                      <div className="score-metric-item">
                        <span className="sm-label">Total Issues</span>
                        <span className="sm-value error">{seo.issues?.length || 0}</span>
                      </div>
                      <div className="score-metric-item">
                        <span className="sm-label">Passed Checks</span>
                        <span className="sm-value success">{seo.passed?.length || 0}</span>
                      </div>
                      <div className="score-metric-item">
                        <span className="sm-label">Internal Links</span>
                        <span className="sm-value">{crawl?.links?.internal ?? 0}</span>
                      </div>
                      <div className="score-metric-item">
                        <span className="sm-label">External Links</span>
                        <span className="sm-value">{crawl?.links?.external ?? 0}</span>
                      </div>
                    </div>
                  </div>

                  {/* Section: Page Information */}
                  <section className="section-saas">
                    <div className="section-header-saas">
                      <h3>Page Information</h3>
                      <span>On-Page Data</span>
                    </div>
                    <div className="saas-table-wrapper">
                      <table className="saas-table compact">
                        <tbody>
                          <tr>
                            <td className="property-name-cell">Page Title</td>
                            <td className="property-value-cell bold-text">
                              {crawl?.seo?.title?.value || <span className="empty-val">Missing</span>}
                            </td>
                          </tr>
                          <tr>
                            <td className="property-name-cell">Meta Description</td>
                            <td className="property-value-cell">
                              {crawl?.seo?.meta_description?.value || <span className="empty-val">Missing</span>}
                            </td>
                          </tr>
                          <tr>
                            <td className="property-name-cell">Canonical URL</td>
                            <td className="property-value-cell">
                              {crawl?.seo?.canonical || <span className="empty-val">Missing</span>}
                            </td>
                          </tr>
                          <tr>
                            <td className="property-name-cell">Primary H1 Heading</td>
                            <td className="property-value-cell">
                              {crawl?.seo?.h1?.values?.[0] || <span className="empty-val">No H1 heading found</span>}
                            </td>
                          </tr>
                          <tr>
                            <td className="property-name-cell">H2 Count</td>
                            <td className="property-value-cell">
                              {crawl?.content?.headings?.h2?.length ?? 0}
                            </td>
                          </tr>
                          <tr>
                            <td className="property-name-cell">Word Count</td>
                            <td className="property-value-cell">
                              {crawl?.content?.word_count ?? 0} words
                            </td>
                          </tr>
                          <tr>
                            <td className="property-name-cell">Images (Total)</td>
                            <td className="property-value-cell">
                              {crawl?.seo?.images?.total ?? 0}
                            </td>
                          </tr>
                          <tr>
                            <td className="property-name-cell">Images Missing Alt Text</td>
                            <td className="property-value-cell">
                              {crawl?.seo?.images?.missing_alt ?? 0}
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </section>

                  {/* Section: Technical & Content Issues */}
                  <section className="section-saas">
                    <div className="section-header-saas">
                      <h3>Page Checklist Issues</h3>
                      <span>Prioritized Checklist</span>
                    </div>
                    {seo.issues?.length > 0 ? (
                      <div className="issues-container-saas">
                        {seo.issues.map((issue, index) => (
                          <div className="issue-row-saas" key={`${issue.category}-${index}`}>
                            <div className="issue-severity-col">
                              <span className={`indicator-dot-saas ${issue.type}`}></span>
                              <span className={`severity-label-saas ${issue.type}`}>{issue.type}</span>
                            </div>
                            <div className="issue-content-col">
                              <span className="issue-category-label">{issue.category}</span>
                              <p className="issue-message-text">{issue.message}</p>
                              {issue.recommendation && (
                                <div className="issue-rec-block">
                                  <strong>Recommendation:</strong> {issue.recommendation}
                                </div>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="empty-state-saas">
                        <h3>No issues detected</h3>
                      </div>
                    )}
                  </section>
                </div>
              ) : (
                // Full Site Overview Dashboard
                <div className="results">
                  {/* Header */}
                  <div className="report-header-saas">
                    <div className="report-title-col">
                      <span className="report-type-badge">Full Site Audit</span>
                      <h2>{siteResult.url}</h2>
                      <a
                        href={siteResult.url}
                        target="_blank"
                        rel="noreferrer"
                        className="report-anchor"
                      >
                        {siteResult.url}
                      </a>
                    </div>
                    <div className="report-actions">
                      <button className="new-analysis" onClick={resetAnalysis}>
                        New Analysis
                      </button>
                    </div>
                  </div>

                  {/* SaaS Score Card */}
                  <div className="score-card-saas">
                    <div className="score-main-col">
                      <span className="score-label-text">Overall Site SEO Score</span>
                      <div className="score-value-row">
                        <span className="score-value-num">{Math.round(averageScore)}</span>
                        <span className="score-value-slash">/100</span>
                        <span className={`score-value-grade ${siteScoreClass}`}>
                          {averageScore >= 90
                            ? "Excellent"
                            : averageScore >= 75
                              ? "Good"
                              : averageScore >= 50
                                ? "Needs Improvement"
                                : "Poor"}
                        </span>
                      </div>
                      <div className="score-bar-bg">
                        <div className={`score-bar-fill ${siteScoreClass}`} style={{ width: `${averageScore}%` }}></div>
                      </div>
                    </div>

                    <div className="score-metrics-col">
                      <div className="score-metric-item">
                        <span className="sm-label">Pages Crawled</span>
                        <span className="sm-value">{siteResult.pages_crawled}</span>
                      </div>
                      <div className="score-metric-item">
                        <span className="sm-label">Average Score</span>
                        <span className="sm-value">{Math.round(averageScore)}</span>
                      </div>
                      <div className="score-metric-item">
                        <span className="sm-label">Good Pages (75+)</span>
                        <span className="sm-value success">{goodPages}</span>
                      </div>
                      <div className="score-metric-item">
                        <span className="sm-label">Needs Attention</span>
                        <span className="sm-value warning">{needsAttention}</span>
                      </div>
                    </div>
                  </div>

                  {/* Stats Grid: Site Overview */}
                  <div className="stats-grid-saas">
                    <div className="stat-card-saas">
                      <span>Highest Page Score</span>
                      <strong>{highestScore}/100</strong>
                    </div>
                    <div className="stat-card-saas">
                      <span>Lowest Page Score</span>
                      <strong>{lowestScore}/100</strong>
                    </div>
                    <div className="stat-card-saas">
                      <span>90+ Score Pages</span>
                      <strong>{excellentPages}</strong>
                    </div>
                    <div className="stat-card-saas">
                      <span>Issue-Free Pages</span>
                      <strong>{issueFreePages}</strong>
                    </div>
                  </div>

                  {/* Distribution Chart & Site Health */}
                  <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "16px", marginBottom: "32px" }}>
                    {/* Score Distribution */}
                    <section style={{ margin: 0 }}>
                      <div className="section-header-saas">
                        <h3>Score Distribution</h3>
                        <span>Page SEO Ranges</span>
                      </div>
                      <div className="distribution-chart-saas">
                        {scoreBuckets.map((bucket) => {
                          const percentage =
                            sitePages.length > 0 ? (bucket.count / sitePages.length) * 100 : 0;
                          return (
                            <div className="dist-row-saas" key={bucket.label}>
                              <div className="dist-label-col">
                                <span className="dist-name-text">{bucket.label}</span>
                                <span className="dist-range-text">{bucket.range}</span>
                              </div>
                              <div className="dist-bar-col">
                                <div className="dist-progress-bg">
                                  <div
                                    className={`dist-progress-fill ${bucket.className}`}
                                    style={{ width: `${percentage}%` }}
                                  ></div>
                                </div>
                              </div>
                              <div className="dist-count-col">
                                <span>{bucket.count}</span>
                                <span className="dist-count-pct">({Math.round(percentage)}%)</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </section>

                    {/* Site Health */}
                    <section style={{ margin: 0 }}>
                      <div className="section-header-saas">
                        <h3>Site Health</h3>
                        <span>Statistics Overview</span>
                      </div>
                      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                        <div className="stat-card-saas sub-text">
                          <span>Pages With Issues</span>
                          <strong>{pagesWithIssues}</strong>
                          <small>Pages requiring checklist corrections</small>
                        </div>
                        <div className="stat-card-saas sub-text">
                          <span>Average Issues / Page</span>
                          <strong>{averageIssues}</strong>
                          <small>Average problems count per page</small>
                        </div>
                      </div>
                    </section>
                  </div>

                  {/* Site-wide Issues Aggregates */}
                  {siteResult.issue_summary && Object.values(siteResult.issue_summary).some((count) => count > 0) && (
                    <section className="section-saas">
                      <div className="section-header-saas">
                        <h3>Site-wide Issues Summary</h3>
                        <span>Consolidated Problems Across Pages</span>
                      </div>
                      <div className="issues-container-saas">
                        {Object.entries(siteResult.issue_summary)
                          .filter(([_, count]) => count > 0)
                          .map(([issueType, count], idx) => {
                            const cleanName = issueType
                              .split("_")
                              .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
                              .join(" ");

                            return (
                              <div className="issue-row-saas" key={`${issueType}-${idx}`} style={{ borderLeft: "4px solid var(--warning)" }}>
                                <div className="issue-severity-col">
                                  <span className="indicator-dot-saas warning"></span>
                                  <span className="severity-label-saas warning">warning</span>
                                </div>
                                <div className="issue-content-col">
                                  <span className="issue-category-label">{cleanName}</span>
                                  <p className="issue-message-text" style={{ margin: 0 }}>
                                    Detected in <strong>{count}</strong> page{count === 1 ? "" : "s"} across the website crawl.
                                  </p>
                                </div>
                              </div>
                            );
                          })}
                      </div>
                    </section>
                  )}

                  {/* Best & Worst Pages */}
                  <section className="section-saas">
                    <div className="section-header-saas">
                      <h3>Page Performance</h3>
                      <span>Outliers & Attention Areas</span>
                    </div>
                    <div className="stats-grid-saas" style={{ gridTemplateColumns: "1fr 1fr" }}>
                      <div className="stat-card-saas hoverable" style={{ cursor: "pointer" }} onClick={() => bestPage && openSitePageAudit(bestPage.url)}>
                        <span>Best Performing Page</span>
                        <strong>{bestPage ? `${bestPage.score}/100` : "—"}</strong>
                        <small>{bestPage ? bestPage.title || bestPage.url : "No pages found"}</small>
                      </div>
                      <div className="stat-card-saas hoverable" style={{ cursor: "pointer" }} onClick={() => worstPage && openSitePageAudit(worstPage.url)}>
                        <span>Highest Priority Attention Area</span>
                        <strong>
                          {worstPage
                            ? worstPage.grade === "Failed"
                              ? "Crawl Failed"
                              : `${worstPage.score}/100`
                            : "—"}
                        </strong>
                        <small>{worstPage ? worstPage.title || worstPage.url : "No pages found"}</small>
                      </div>
                    </div>
                  </section>

                  {/* Crawler Table */}
                  <section className="section-saas">
                    <div className="section-header-saas">
                      <h3>Crawled Pages</h3>
                      <span>{siteResult.pages_crawled} URL Paths Crawled</span>
                    </div>

                    <div className="saas-table-wrapper">
                      <table className="saas-table">
                        <thead>
                          <tr>
                            <th>Page URL / Title</th>
                            <th>Score</th>
                            <th>Grade</th>
                            <th>Checklist Issues</th>
                          </tr>
                        </thead>
                        <tbody>
                          {(siteResult.pages || []).map((page, index) => {
                            const pageScore = Number(page.score) || 0;
                            const pageScoreClass =
                              pageScore >= 90
                                ? "excellent"
                                : pageScore >= 75
                                  ? "good"
                                  : pageScore >= 50
                                    ? "needs-improvement"
                                    : "poor";

                            return (
                              <tr
                                className="table-row-clickable"
                                key={`${page.url}-${index}`}
                                onClick={() => openSitePageAudit(page.url)}
                              >
                                <td>
                                  <div className="table-cell-title">
                                    {page.title || "Failed to load"}
                                  </div>
                                  <div className="table-cell-url">{page.url}</div>
                                </td>
                                <td>
                                  <span className="table-cell-score">
                                    {page.grade === "Failed" ? "—" : page.score}
                                  </span>
                                </td>
                                <td>
                                  <span className={`score-badge ${pageScoreClass}`}>
                                    {page.grade === "Failed"
                                      ? page.status_code
                                        ? `Error (HTTP ${page.status_code})`
                                        : "Error"
                                      : page.grade}
                                  </span>
                                </td>
                                <td>{page.issues ?? 0}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                  </section>
                </div>
              )
            ) : (
              <div className="empty-state-saas">
                <div className="empty-state-icon">🌐</div>
                <h3>No Site Audit Report</h3>
                <p>Run a Site Audit on the Dashboard to see crawled pages and health scores.</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );

  // Helper method to toggle views cleanly
  function handleNavClick(tabName) {
    setActiveTab(tabName);
    setError("");
  }
}

export default App;