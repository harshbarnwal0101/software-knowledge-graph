"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { repoApi, authApi } from "@/lib/api";

export default function DashboardPage() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }

    Promise.all([authApi.me(), repoApi.list()])
      .then(([userRes, repoRes]) => {
        setUser(userRes.data);
        setRepos(repoRes.data);
      })
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  if (loading) return (
    <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <span className="text-muted text-sm">Loading…</span>
    </div>
  );

  const totalFiles = repos.reduce((s, r) => s + r.total_files, 0);
  const totalClasses = repos.reduce((s, r) => s + r.total_classes, 0);
  const totalFunctions = repos.reduce((s, r) => s + r.total_functions, 0);

  return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        {/* Header */}
        <div className="topnav">
          <span style={{ flex: 1, fontWeight: 500, fontSize: "0.9375rem" }}>Dashboard</span>
          <span className="text-muted text-sm">{user?.username}</span>
        </div>

        <div className="page-body">
          {/* Welcome */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: 0 }}>
              Welcome back{user ? `, ${user.username}` : ""}
            </h1>
            <p className="text-muted text-sm" style={{ marginTop: "0.25rem" }}>
              {repos.length === 0
                ? "Add your first repository to get started."
                : `You have ${repos.length} repositor${repos.length === 1 ? "y" : "ies"} indexed.`}
            </p>
          </div>

          {/* Stats */}
          <div className="grid-4" style={{ marginBottom: "1.5rem" }}>
            {[
              { label: "Repositories", value: repos.length },
              { label: "Files Indexed", value: totalFiles },
              { label: "Classes Found", value: totalClasses },
              { label: "Functions Found", value: totalFunctions },
            ].map((stat) => (
              <div key={stat.label} className="card stat-card">
                <div className="stat-value">{stat.value}</div>
                <div className="stat-label">{stat.label}</div>
              </div>
            ))}
          </div>

          {/* Repositories */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.875rem" }}>
            <h2 style={{ fontSize: "0.9375rem", fontWeight: 600, margin: 0 }}>Repositories</h2>
            <Link href="/repositories/new" className="btn btn-primary btn-sm">
              + Add Repository
            </Link>
          </div>

          {repos.length === 0 ? (
            <div className="card">
              <div className="empty-state">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: "0 auto" }}>
                  <path d="M3 7l9-4 9 4v10l-9 4-9-4V7z" />
                  <path d="M12 3v18M3 7l9 4 9-4" />
                </svg>
                <h3>No repositories yet</h3>
                <p>Add a GitHub repository to start exploring your codebase as a knowledge graph.</p>
                <Link href="/repositories/new" className="btn btn-primary" style={{ marginTop: "0.75rem" }}>
                  Add Repository
                </Link>
              </div>
            </div>
          ) : (
            <div className="card table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Repository</th>
                    <th>Status</th>
                    <th>Files</th>
                    <th>Classes</th>
                    <th>Functions</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {repos.map((repo) => (
                    <tr key={repo.id}>
                      <td>
                        <div style={{ fontWeight: 500 }}>{repo.name}</div>
                        <div className="text-xs text-muted truncate" style={{ maxWidth: "240px" }}>
                          {repo.github_url}
                        </div>
                      </td>
                      <td>
                        <StatusBadge status={repo.status} />
                      </td>
                      <td>{repo.total_files}</td>
                      <td>{repo.total_classes}</td>
                      <td>{repo.total_functions}</td>
                      <td>
                        <Link href={`/repositories/${repo.id}`} className="btn btn-secondary btn-sm">
                          Open
                        </Link>
                      </td>
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

function StatusBadge({ status }) {
  const map = {
    ready: ["badge-success", "Ready"],
    pending: ["badge-pending", "Pending"],
    failed: ["badge-error", "Failed"],
    cloning: ["badge-pending", "Cloning…"],
    parsing: ["badge-pending", "Parsing…"],
    building_graph: ["badge-pending", "Building graph…"],
    embedding: ["badge-pending", "Embedding…"],
  };
  const [cls, label] = map[status] || ["badge-default", status];
  return <span className={`badge ${cls}`}>{label}</span>;
}
