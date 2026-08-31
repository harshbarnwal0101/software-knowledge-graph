"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import api, { repoApi } from "@/lib/api";

export default function GitHistoryPage() {
  const { id } = useParams();
  const router = useRouter();

  const [repo, setRepo] = useState(null);
  const [commits, setCommits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }

    Promise.all([
      repoApi.get(id),
      api.get(`/api/repositories/${id}/history`)
    ]).then(([repoRes, historyRes]) => {
      setRepo(repoRes.data);
      setCommits(historyRes.data.commits || []);
    }).catch(() => router.replace("/repositories"))
      .finally(() => setLoading(false));
  }, [id, router]);

  if (loading) return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div style={{ padding: "2rem", color: "var(--muted-foreground)", fontSize: "0.875rem" }}>Loading commit history…</div>
      </main>
    </div>
  );

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
            <span style={{ color: "var(--foreground)", fontWeight: 500 }}>Git History</span>
          </nav>
        </div>

        <div className="page-body" style={{ maxWidth: "800px" }}>
          {/* Header */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: "0 0 0.25rem" }}>
              Git Commit History & Insights
            </h1>
            <p className="text-sm text-muted">
              Inspect commit logs extracted from repository cloning.
            </p>
          </div>

          {/* Commit Timeline */}
          {commits.length === 0 ? (
            <div className="card">
              <div className="empty-state">
                <p>No git commit history available for this repository.</p>
              </div>
            </div>
          ) : (
            <div className="card table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Commit Hash</th>
                    <th>Message</th>
                    <th>Author</th>
                    <th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {commits.map((c) => (
                    <tr key={c.hash}>
                      <td>
                        <span className="font-mono text-xs text-muted" style={{ background: "var(--muted)", padding: "2px 6px", borderRadius: "4px" }}>
                          {c.hash.slice(0, 7)}
                        </span>
                      </td>
                      <td style={{ fontWeight: 500 }}>{c.message}</td>
                      <td className="text-sm text-muted">{c.author_name}</td>
                      <td className="text-xs text-muted font-mono">{c.date.slice(0, 10)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
