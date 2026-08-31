"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { repoApi } from "@/lib/api";

const COMING_SOON = ["Graph", "Explorer", "AI Chat", "Search", "History", "Health"];

export default function RepositoryPage() {
  const { id } = useParams();
  const router = useRouter();
  const [repo, setRepo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    repoApi.get(id)
      .then((res) => setRepo(res.data))
      .catch(() => router.replace("/repositories"))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div style={{ padding: "2rem", color: "var(--muted-foreground)", fontSize: "0.875rem" }}>Loading…</div>
      </main>
    </div>
  );

  if (!repo) return null;

  const statusColor = {
    ready: "#22c55e", pending: "#f59e0b", failed: "#ef4444"
  }[repo.status] || "#a1a1aa";

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
          <a href={repo.github_url} target="_blank" rel="noopener noreferrer" className="btn btn-secondary btn-sm">
            View on GitHub ↗
          </a>
        </div>

        <div className="page-body">
          {/* Repo header */}
          <div style={{ marginBottom: "1.5rem" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.625rem", marginBottom: "0.375rem" }}>
              <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: 0 }}>{repo.name}</h1>
              <div style={{
                display: "flex", alignItems: "center", gap: "0.375rem",
                fontSize: "0.8125rem", color: "var(--muted-foreground)"
              }}>
                <div className="status-dot" style={{ background: statusColor }} />
                {repo.status}
              </div>
            </div>
            {repo.description && (
              <p className="text-sm text-muted">{repo.description}</p>
            )}
            <p className="text-xs text-muted" style={{ marginTop: "0.25rem" }}>
              <a href={repo.github_url} target="_blank" rel="noopener noreferrer" style={{ color: "inherit" }}>
                {repo.github_url}
              </a>
            </p>
          </div>

          {/* Stats */}
          <div className="grid-4" style={{ marginBottom: "1.5rem" }}>
            {[
              { label: "Files", value: repo.total_files },
              { label: "Lines of Code", value: repo.total_lines },
              { label: "Classes", value: repo.total_classes },
              { label: "Functions", value: repo.total_functions },
            ].map((stat) => (
              <div key={stat.label} className="card stat-card">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Status message */}
          {repo.status_message && (
            <div style={{
              padding: "0.75rem 1rem", background: "var(--muted)",
              border: "1px solid var(--border)", borderRadius: "var(--radius)",
              fontSize: "0.875rem", marginBottom: "1.5rem"
            }}>
              {repo.status_message}
            </div>
          )}

          {/* Features grid */}
          <h2 style={{ fontSize: "0.9375rem", fontWeight: 600, margin: "0 0 0.875rem" }}>Features</h2>
          <div className="grid-3">
            {COMING_SOON.map((feature) => (
              <div key={feature} className="card" style={{ padding: "1.25rem", opacity: 0.6 }}>
                <div style={{ fontWeight: 500, marginBottom: "0.25rem" }}>{feature}</div>
                <div className="text-xs text-muted">Coming in a future phase</div>
              </div>
            ))}
          </div>

          {/* Analysis CTA */}
          {repo.status === "pending" && (
            <div style={{
              marginTop: "1.5rem", padding: "1.25rem",
              background: "var(--muted)", border: "1px solid var(--border)",
              borderRadius: "var(--radius)"
            }}>
              <div style={{ fontWeight: 500, marginBottom: "0.375rem" }}>Ready to analyze</div>
              <p className="text-sm text-muted" style={{ marginBottom: "0.875rem" }}>
                Full repository analysis (cloning, parsing, graph building, embeddings) is coming in Phase 2.
                The repository has been registered successfully.
              </p>
              <button className="btn btn-primary" disabled>
                Analyze Repository — Coming in Phase 2
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
