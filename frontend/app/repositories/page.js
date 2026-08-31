"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { repoApi } from "@/lib/api";

export default function RepositoriesPage() {
  const router = useRouter();
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }
    repoApi.list()
      .then((res) => setRepos(res.data))
      .catch(() => router.replace("/login"))
      .finally(() => setLoading(false));
  }, [router]);

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    await repoApi.delete(id);
    setRepos(repos.filter((r) => r.id !== id));
  };

  return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div className="topnav">
          <span style={{ flex: 1, fontWeight: 500, fontSize: "0.9375rem" }}>Repositories</span>
          <Link href="/repositories/new" className="btn btn-primary btn-sm">+ Add Repository</Link>
        </div>

        <div className="page-body">
          {loading ? (
            <p className="text-muted text-sm">Loading…</p>
          ) : repos.length === 0 ? (
            <div className="card">
              <div className="empty-state">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ margin: "0 auto" }}>
                  <path d="M3 7l9-4 9 4v10l-9 4-9-4V7z" /><path d="M12 3v18M3 7l9 4 9-4" />
                </svg>
                <h3>No repositories yet</h3>
                <p>Add a GitHub repository to start building its knowledge graph.</p>
                <Link href="/repositories/new" className="btn btn-primary" style={{ marginTop: "0.75rem" }}>Add Repository</Link>
              </div>
            </div>
          ) : (
            <div className="card table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>URL</th>
                    <th>Status</th>
                    <th>Files</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {repos.map((repo) => (
                    <tr key={repo.id}>
                      <td style={{ fontWeight: 500 }}>{repo.name}</td>
                      <td>
                        <a href={repo.github_url} target="_blank" rel="noopener noreferrer"
                          className="text-sm text-muted" style={{ textDecoration: "underline" }}>
                          {repo.github_url.replace("https://github.com/", "")}
                        </a>
                      </td>
                      <td>
                        <span className={`badge ${statusClass(repo.status)}`}>{repo.status}</span>
                      </td>
                      <td>{repo.total_files}</td>
                      <td style={{ display: "flex", gap: "0.5rem" }}>
                        <Link href={`/repositories/${repo.id}`} className="btn btn-secondary btn-sm">Open</Link>
                        <button onClick={() => handleDelete(repo.id, repo.name)} className="btn btn-destructive btn-sm">Delete</button>
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

function statusClass(status) {
  const map = { ready: "badge-success", pending: "badge-pending", failed: "badge-error" };
  return map[status] || "badge-default";
}
