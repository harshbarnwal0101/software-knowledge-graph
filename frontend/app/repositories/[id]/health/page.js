"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import api, { repoApi } from "@/lib/api";

export default function RepositoryHealthPage() {
  const { id } = useParams();
  const router = useRouter();

  const [repo, setRepo] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }

    Promise.all([
      repoApi.get(id),
      api.get(`/api/repositories/${id}/health`)
    ]).then(([repoRes, healthRes]) => {
      setRepo(repoRes.data);
      setHealthData(healthRes.data);
    }).catch(() => router.replace("/repositories"))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div style={{ padding: "2rem", color: "var(--muted-foreground)", fontSize: "0.875rem" }}>Auditing repository health…</div>
      </main>
    </div>
  );

  const score = healthData?.health_score || 85;

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
            <span style={{ color: "var(--foreground)", fontWeight: 500 }}>Repository Health</span>
          </nav>
        </div>

        <div className="page-body" style={{ maxWidth: "800px" }}>
          {/* Header */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: "0 0 0.25rem" }}>
              Codebase Health & Quality Audit
            </h1>
            <p className="text-sm text-muted">
              Heuristic analysis of file sizes, missing documentation, and potential complexity hotspots.
            </p>
          </div>

          {/* Health Score Card */}
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem", display: "flex", alignItems: "center", gap: "1.5rem" }}>
            <div style={{
              width: "4.5rem", height: "4.5rem", borderRadius: "50%",
              background: score >= 80 ? "#dcfce7" : score >= 60 ? "#fef9c3" : "#fee2e2",
              color: score >= 80 ? "#166534" : score >= 60 ? "#854d0e" : "#991b1b",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: "1.75rem", fontWeight: 700, flexShrink: 0
            }}>
              {score}
            </div>
            <div>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: "0 0 0.25rem" }}>
                {score >= 80 ? "Good Code Health" : score >= 60 ? "Moderate Complexity" : "High Complexity Risk"}
              </h3>
              <p className="text-sm text-muted" style={{ margin: 0 }}>
                Repository meets standard modularity guidelines. Inspect potential hotspots below to improve maintainability.
              </p>
            </div>
          </div>

          {/* Hotspots */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
            {/* Large Files */}
            <div className="card" style={{ padding: "1.25rem" }}>
              <h4 style={{ fontSize: "0.9375rem", fontWeight: 600, margin: "0 0 0.75rem" }}>
                Large Files (&gt;300 Lines)
              </h4>
              {healthData?.large_files?.length === 0 ? (
                <p className="text-sm text-muted">No oversized files detected.</p>
              ) : (
                <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.8125rem" }}>
                  {healthData?.large_files?.map((f, i) => (
                    <li key={i} className="font-mono text-muted" style={{ padding: "0.2rem 0" }}>{f}</li>
                  ))}
                </ul>
              )}
            </div>

            {/* Missing Docstrings */}
            <div className="card" style={{ padding: "1.25rem" }}>
              <h4 style={{ fontSize: "0.9375rem", fontWeight: 600, margin: "0 0 0.75rem" }}>
                Missing Docstrings
              </h4>
              {healthData?.missing_docstrings?.length === 0 ? (
                <p className="text-sm text-muted">All key symbols have docstrings.</p>
              ) : (
                <ul style={{ margin: 0, paddingLeft: "1.25rem", fontSize: "0.8125rem" }}>
                  {healthData?.missing_docstrings?.map((s, i) => (
                    <li key={i} className="font-mono text-muted" style={{ padding: "0.2rem 0" }}>{s}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
