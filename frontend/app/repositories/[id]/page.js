"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { repoApi } from "@/lib/api";
import api from "@/lib/api";

const PIPELINE_STEPS = [
  { key: "pending",        label: "Queued for analysis" },
  { key: "cloning",        label: "Cloning repository" },
  { key: "parsing",        label: "Parsing source files" },
  { key: "building_graph", label: "Building knowledge graph" },
  { key: "embedding",      label: "Generating embeddings" },
  { key: "ready",          label: "Analysis complete" },
];

const STATUS_ORDER = ["pending", "cloning", "parsing", "building_graph", "embedding", "ready"];

function getStepState(stepKey, currentStatus) {
  const stepIdx = STATUS_ORDER.indexOf(stepKey);
  const currentIdx = STATUS_ORDER.indexOf(currentStatus);
  if (currentStatus === "failed") return stepIdx <= currentIdx ? "done" : "pending";
  if (stepIdx < currentIdx) return "done";
  if (stepIdx === currentIdx) return "active";
  return "pending";
}

export default function RepositoryPage() {
  const { id } = useParams();
  const router = useRouter();
  const [repo, setRepo] = useState(null);
  const [files, setFiles] = useState([]);
  const [symbols, setSymbols] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState("overview");
  const [logs, setLogs] = useState([]);
  const pollRef = useRef(null);

  useEffect(() => {
    if (repo && repo.status_message) {
      setLogs((prev) => {
        if (prev.length === 0 || prev[prev.length - 1].message !== repo.status_message) {
          return [...prev, { time: new Date().toLocaleTimeString(), message: repo.status_message }];
        }
        return prev;
      });
    }
  }, [repo?.status_message]);

  const fetchRepo = useCallback(async () => {
    try {
      const res = await repoApi.get(id);
      setRepo(res.data);
      return res.data;
    } catch {
      router.replace("/repositories");
    }
  }, [id, router]);

  const fetchDetails = useCallback(async () => {
    const [filesRes, symbolsRes] = await Promise.allSettled([
      api.get(`/api/repositories/${id}/files`),
      api.get(`/api/repositories/${id}/symbols?limit=200`),
    ]);
    if (filesRes.status === "fulfilled") setFiles(filesRes.value.data);
    if (symbolsRes.status === "fulfilled") setSymbols(symbolsRes.value.data);
  }, [id]);

  const startPolling = useCallback(() => {
    if (pollRef.current) return;
    pollRef.current = setInterval(async () => {
      const r = await fetchRepo();
      if (r && (r.status === "ready" || r.status === "failed")) {
        clearInterval(pollRef.current);
        pollRef.current = null;
        setAnalyzing(false);
        if (r.status === "ready") fetchDetails();
      }
    }, 2000);
  }, [fetchRepo, fetchDetails]);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }

    fetchRepo().then((r) => {
      setLoading(false);
      if (!r) return;
      const inProgress = ["cloning","parsing","building_graph","embedding","pending"].includes(r.status);
      if (inProgress) { setAnalyzing(true); startPolling(); }
      else if (r.status === "ready") fetchDetails();
    });

    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchRepo, fetchDetails, startPolling, router]);

  const handleAnalyze = async () => {
    setAnalyzing(true);
    try {
      await repoApi.analyze(id);
      startPolling();
    } catch (err) {
      alert(err.response?.data?.detail || "Failed to start analysis");
      setAnalyzing(false);
    }
  };

  if (loading) return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div style={{ padding: "2rem", color: "var(--muted-foreground)", fontSize: "0.875rem" }}>Loading…</div>
      </main>
    </div>
  );

  if (!repo) return null;

  const isReady = repo.status === "ready";
  const isFailed = repo.status === "failed";
  const isInProgress = analyzing || ["cloning","parsing","building_graph","embedding"].includes(repo.status);

  const classes = symbols.filter(s => s.type === "class");
  const functions = symbols.filter(s => s.type === "function" || s.type === "method");
  const imports = symbols.filter(s => s.type === "import");

  const langCount = {};
  files.forEach(f => { langCount[f.language] = (langCount[f.language] || 0) + 1; });

  return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        {/* Topnav */}
        <div className="topnav">
          <nav className="text-sm text-muted" style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <Link href="/repositories" style={{ color: "inherit", textDecoration: "none" }}>Repositories</Link>
            <span>/</span>
            <span style={{ color: "var(--foreground)", fontWeight: 500 }}>{repo.name}</span>
          </nav>
          <div style={{ flex: 1 }} />
          {isReady && (
            <Link href={`/repositories/${id}/graph`} className="btn btn-secondary btn-sm" style={{ color: "#38bdf8" }}>
              📊 Open Graph Explorer
            </Link>
          )}
          <a href={repo.github_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
            GitHub ↗
          </a>
          {!isInProgress && (
            <button
              className="btn btn-primary btn-sm"
              onClick={handleAnalyze}
              disabled={analyzing}
            >
              {isFailed ? "Retry Analysis" : isReady ? "Re-analyze" : "Analyze"}
            </button>
          )}
        </div>

        <div className="page-body">
          {/* Header */}
          <div style={{ marginBottom: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.25rem" }}>
              <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: 0 }}>{repo.name}</h1>
              <StatusBadge status={repo.status} />
            </div>
            {repo.description && <p className="text-sm text-muted">{repo.description}</p>}
            <p className="text-xs text-muted" style={{ marginTop: "0.25rem" }}>
              <a href={repo.github_url} target="_blank" rel="noopener noreferrer" style={{ color: "inherit" }}>{repo.github_url}</a>
            </p>
          </div>

          {/* Ingestion Progress */}
          {(isInProgress || isFailed) && (
            <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
              <div style={{ fontWeight: 500, marginBottom: "1rem", fontSize: "0.9375rem" }}>
                {isFailed ? "Analysis Failed" : "Analyzing Repository…"}
              </div>
              <div className="progress-steps">
                {PIPELINE_STEPS.map((step) => {
                  const state = getStepState(step.key, repo.status);
                  return (
                    <div key={step.key} className={`progress-step step-${state}`}>
                      <span className="step-icon">
                        {state === "done"   ? "✓" :
                         state === "active" ? <Spinner /> : "○"}
                      </span>
                      <span>{step.label}</span>
                    </div>
                  );
                })}
              </div>
              {isFailed && repo.status_message && (
                <div style={{
                  marginTop: "1rem", padding: "0.625rem 0.75rem",
                  background: "#fee2e2", border: "1px solid #fecaca",
                  borderRadius: "var(--radius)", fontSize: "0.8125rem", color: "#991b1b"
                }}>
                  {repo.status_message}
                </div>
              )}
            </div>
          )}

          {/* Terminal Sandbox */}
          {(isInProgress || logs.length > 0) && (
            <div className="card" style={{ background: "#0f172a", color: "#e2e8f0", padding: "1rem", fontFamily: "monospace", fontSize: "0.875rem", marginBottom: "1.5rem", borderRadius: "0.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid #334155", paddingBottom: "0.5rem", marginBottom: "0.75rem" }}>
                <div style={{ fontWeight: "bold", color: "#38bdf8" }}>Analysis Terminal</div>
                {isInProgress && <Spinner />}
              </div>
              <div style={{ minHeight: "120px", maxHeight: "250px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "0.25rem" }}>
                {logs.map((log, i) => (
                  <div key={i}>
                    <span style={{ color: "#64748b", marginRight: "0.5rem" }}>[{log.time}]</span>
                    <span style={{ color: log.message.toLowerCase().includes("failed") ? "#ef4444" : "#a7f3d0" }}>{log.message}</span>
                  </div>
                ))}
                {isInProgress && (
                  <div style={{ color: "#94a3b8", animation: "pulse 1.5s infinite" }}>_</div>
                )}
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="grid-4" style={{ marginBottom: "1.5rem" }}>
            {[
              { label: "Files", value: repo.total_files },
              { label: "Lines of Code", value: repo.total_lines.toLocaleString() },
              { label: "Classes", value: repo.total_classes },
              { label: "Functions", value: repo.total_functions },
            ].map((stat) => (
              <div key={stat.label} className="card stat-card">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Tabs */}
          {isReady && (
            <>
              <div style={{ display: "flex", gap: "0.125rem", borderBottom: "1px solid var(--border)", marginBottom: "1.25rem" }}>
                {["overview","files","classes","functions","imports"].map((tab) => (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className="btn btn-ghost"
                    style={{
                      borderRadius: "var(--radius) var(--radius) 0 0",
                      borderBottom: activeTab === tab ? "2px solid var(--foreground)" : "2px solid transparent",
                      fontWeight: activeTab === tab ? 600 : 400,
                      color: activeTab === tab ? "var(--foreground)" : "var(--muted-foreground)",
                    }}
                  >
                    {tab.charAt(0).toUpperCase() + tab.slice(1)}
                    <span style={{ marginLeft: "0.375rem", fontSize: "0.75rem", opacity: 0.6 }}>
                      {tab === "files" ? files.length :
                       tab === "classes" ? classes.length :
                       tab === "functions" ? functions.length :
                       tab === "imports" ? imports.length : ""}
                    </span>
                  </button>
                ))}
              </div>

              {activeTab === "overview" && <OverviewTab repoId={id} files={files} langCount={langCount} symbols={symbols} />}
              {activeTab === "files" && <FilesTab files={files} />}
              {activeTab === "classes" && <SymbolsTab symbols={classes} label="Classes" />}
              {activeTab === "functions" && <SymbolsTab symbols={functions} label="Functions & Methods" />}
              {activeTab === "imports" && <SymbolsTab symbols={imports} label="Imports" />}
            </>
          )}

          {/* Not yet analyzed */}
          {repo.status === "pending" && !isInProgress && (
            <div className="card" style={{ padding: "1.5rem" }}>
              <div style={{ fontWeight: 500, marginBottom: "0.375rem" }}>Ready to analyze</div>
              <p className="text-sm text-muted" style={{ marginBottom: "1rem" }}>
                Click <strong>Start Analysis</strong> to clone the repository, parse source files,
                extract symbols, and generate the interactive software knowledge graph.
              </p>
              <button className="btn btn-primary" onClick={handleAnalyze}>
                Start Analysis
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function OverviewTab({ repoId, files, langCount, symbols }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div className="card" style={{ padding: "1.25rem", background: "linear-gradient(135deg, rgba(30,41,59,0.5) 0%, rgba(15,23,42,0.5) 100%)" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div>
            <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: "0 0 0.25rem" }}>Software Knowledge Graph Ready</h3>
            <p className="text-sm text-muted">Explore files, functions, classes, and dependencies as an interactive node graph.</p>
          </div>
          <Link href={`/repositories/${repoId}/graph`} className="btn btn-primary">
            Explore Graph ➔
          </Link>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontWeight: 500, marginBottom: "0.875rem", fontSize: "0.9375rem" }}>Languages</div>
          {Object.entries(langCount).sort((a, b) => b[1] - a[1]).map(([lang, count]) => (
            <div key={lang} style={{ display: "flex", justifyContent: "space-between", padding: "0.375rem 0", borderBottom: "1px solid var(--border)", fontSize: "0.875rem" }}>
              <span style={{ textTransform: "capitalize" }}>{lang}</span>
              <span className="text-muted">{count} files</span>
            </div>
          ))}
        </div>
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ fontWeight: 500, marginBottom: "0.875rem", fontSize: "0.9375rem" }}>Symbol Breakdown</div>
          {[
            ["Classes", symbols.filter(s => s.type === "class").length],
            ["Functions", symbols.filter(s => s.type === "function").length],
            ["Methods", symbols.filter(s => s.type === "method").length],
            ["Imports", symbols.filter(s => s.type === "import").length],
          ].map(([label, count]) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "0.375rem 0", borderBottom: "1px solid var(--border)", fontSize: "0.875rem" }}>
              <span>{label}</span>
              <span className="text-muted">{count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function FilesTab({ files }) {
  const [search, setSearch] = useState("");
  const filtered = files.filter(f => f.path.toLowerCase().includes(search.toLowerCase()));
  return (
    <div>
      <input className="input" placeholder="Filter files…" value={search}
        onChange={e => setSearch(e.target.value)} style={{ marginBottom: "0.875rem", maxWidth: "320px" }} />
      <div className="card table-wrapper">
        <table>
          <thead><tr><th>Path</th><th>Language</th><th>Lines</th><th>Size</th></tr></thead>
          <tbody>
            {filtered.slice(0, 200).map(f => (
              <tr key={f.id}>
                <td className="font-mono text-sm">{f.path}</td>
                <td><span className="badge badge-default">{f.language}</span></td>
                <td className="text-sm text-muted">{f.lines}</td>
                <td className="text-sm text-muted">{(f.size_bytes / 1024).toFixed(1)} KB</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SymbolsTab({ symbols, label }) {
  const [search, setSearch] = useState("");
  const filtered = symbols.filter(s =>
    s.name.toLowerCase().includes(search.toLowerCase()) ||
    s.file_path.toLowerCase().includes(search.toLowerCase())
  );
  return (
    <div>
      <input className="input" placeholder={`Search ${label.toLowerCase()}…`} value={search}
        onChange={e => setSearch(e.target.value)} style={{ marginBottom: "0.875rem", maxWidth: "320px" }} />
      <div className="card table-wrapper">
        <table>
          <thead><tr><th>Name</th><th>File</th><th>Line</th><th>Language</th></tr></thead>
          <tbody>
            {filtered.slice(0, 200).map(s => (
              <tr key={s.id}>
                <td>
                  <div style={{ fontWeight: 500, fontSize: "0.875rem" }}>{s.name}</div>
                  {s.signature && <div className="text-xs text-muted font-mono">{s.signature}</div>}
                  {s.parent_name && <div className="text-xs text-muted">in {s.parent_name}</div>}
                </td>
                <td className="font-mono text-xs text-muted">{s.file_path}</td>
                <td className="text-sm text-muted">{s.line_start}</td>
                <td><span className="badge badge-default">{s.language}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    ready:          "badge-success",
    pending:        "badge-pending",
    failed:         "badge-error",
    cloning:        "badge-pending",
    parsing:        "badge-pending",
    building_graph: "badge-pending",
    embedding:      "badge-pending",
  };
  return <span className={`badge ${map[status] || "badge-default"}`}>{status.replace(/_/g," ")}</span>;
}

function Spinner() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"
      style={{ animation: "spin 1s linear infinite", display: "inline-block" }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
    </svg>
  );
}
