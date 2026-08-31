"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import api, { repoApi } from "@/lib/api";

export default function ImpactAnalysisPage() {
  const { id } = useParams();
  const router = useRouter();

  const [repo, setRepo] = useState(null);
  const [symbols, setSymbols] = useState([]);
  const [targetName, setTargetName] = useState("");
  const [impactData, setImpactData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }

    Promise.all([
      repoApi.get(id),
      api.get(`/api/repositories/${id}/symbols?limit=50`)
    ]).then(([repoRes, symRes]) => {
      setRepo(repoRes.data);
      setSymbols(symRes.data || []);
      if (symRes.data && symRes.data.length > 0) {
        const first = symRes.data[0].name;
        setTargetName(first);
        runImpact(first);
      }
    }).catch(() => router.replace("/repositories"));
  }, [id, router]);

  const runImpact = async (symbolToAnalyze) => {
    const name = symbolToAnalyze || targetName;
    if (!name) return;
    setLoading(true);
    try {
      const res = await api.post(`/api/repositories/${id}/impact-analysis`, { target_name: name });
      setImpactData(res.data);
    } catch (err) {
      console.error("Impact analysis failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    runImpact(targetName);
  };

  return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        {/* Topnav */}
        <div className="topnav">
          <nav className="text-sm text-muted" style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <Link href="/repositories" style={{ color: "inherit", textDecoration: "none" }}>Repositories</Link>
            <span>/</span>
            <Link href={`/repositories/${id}`} style={{ color: "inherit", textDecoration: "none" }}>{repo?.name}</Link>
            <span>/</span>
            <span style={{ color: "var(--foreground)", fontWeight: 500 }}>Impact Analysis</span>
          </nav>
        </div>

        <div className="page-body" style={{ maxWidth: "800px" }}>
          {/* Header */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: "0 0 0.25rem" }}>
              Code Impact & Change Risk Analysis
            </h1>
            <p className="text-sm text-muted">
              Analyze multi-hop dependency chains in the knowledge graph before refactoring or changing a module.
            </p>
          </div>

          {/* Target Selector */}
          <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
            <form onSubmit={handleFormSubmit} style={{ display: "flex", gap: "0.75rem", alignItems: "flex-end" }}>
              <div style={{ flex: 1 }}>
                <label className="label">Target Symbol or Class</label>
                <input
                  className="input"
                  placeholder="e.g. UserService or UserRepository"
                  value={targetName}
                  onChange={(e) => setTargetName(e.target.value)}
                />
              </div>
              <button type="submit" className="btn btn-primary" disabled={loading}>
                {loading ? "Analyzing…" : "Analyze Impact"}
              </button>
            </form>

            {/* Quick chips */}
            {symbols.length > 0 && (
              <div style={{ display: "flex", gap: "0.375rem", marginTop: "0.75rem", flexWrap: "wrap", alignItems: "center" }}>
                <span className="text-xs text-muted">Quick select:</span>
                {symbols.slice(0, 6).map((s) => (
                  <button
                    key={s.id}
                    className="btn btn-ghost btn-sm font-mono text-xs"
                    onClick={() => { setTargetName(s.name); runImpact(s.name); }}
                  >
                    {s.name}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Results */}
          {impactData && (
            <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
              {/* Risk Banner */}
              <div className="card" style={{
                padding: "1.25rem",
                borderLeft: `4px solid ${
                  impactData.impact_level === "HIGH" ? "#ef4444" :
                  impactData.impact_level === "MEDIUM" ? "#f59e0b" : "#22c55e"
                }`
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.5rem" }}>
                  <h3 style={{ fontSize: "1rem", fontWeight: 600, margin: 0 }}>
                    Target: <span className="font-mono">{impactData.target.name}</span>
                  </h3>
                  <span className={`badge ${
                    impactData.impact_level === "HIGH" ? "badge-error" :
                    impactData.impact_level === "MEDIUM" ? "badge-warning" : "badge-success"
                  }`}>
                    Impact Level: {impactData.impact_level}
                  </span>
                </div>
                <p className="text-sm text-muted" style={{ margin: 0 }}>
                  {impactData.risk_explanation}
                </p>
              </div>

              {/* Direct Dependents */}
              <div className="card" style={{ padding: "1.25rem" }}>
                <h4 style={{ fontSize: "0.9375rem", fontWeight: 600, margin: "0 0 0.875rem" }}>
                  Direct Dependents ({impactData.direct_dependents.length})
                </h4>
                {impactData.direct_dependents.length === 0 ? (
                  <p className="text-sm text-muted">No direct downstream dependents found.</p>
                ) : (
                  <div className="table-wrapper">
                    <table>
                      <thead><tr><th>Dependent</th><th>Relation</th><th>File</th></tr></thead>
                      <tbody>
                        {impactData.direct_dependents.map((dep, idx) => (
                          <tr key={idx}>
                            <td className="font-mono text-sm" style={{ fontWeight: 500 }}>{dep.name}</td>
                            <td><span className="badge badge-default">{dep.relation}</span></td>
                            <td className="font-mono text-xs text-muted">{dep.file_path}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Recommended Unit Tests */}
              <div className="card" style={{ padding: "1.25rem" }}>
                <h4 style={{ fontSize: "0.9375rem", fontWeight: 600, margin: "0 0 0.875rem" }}>
                  Recommended Test Suite
                </h4>
                {impactData.recommended_tests.length === 0 ? (
                  <p className="text-sm text-muted">No test files detected in repository.</p>
                ) : (
                  <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.875rem" }}>
                    {impactData.recommended_tests.map((testFile, idx) => (
                      <li key={idx} className="font-mono text-sm text-muted" style={{ padding: "0.25rem 0" }}>
                        {testFile}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
