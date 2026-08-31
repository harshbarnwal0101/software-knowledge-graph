"use client";
import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import api, { repoApi } from "@/lib/api";

export default function SearchPage() {
  const { id } = useParams();
  const router = useRouter();

  const [repo, setRepo] = useState(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }
    repoApi.get(id).then((res) => setRepo(res.data)).catch(() => router.replace("/repositories"));
  }, [id, router]);

  const handleSearch = async (e) => {
    e?.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setHasSearched(true);

    try {
      const res = await api.post(`/api/repositories/${id}/search`, { query, limit: 20 });
      setResults(res.data.results || []);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
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
            <span style={{ color: "var(--foreground)", fontWeight: 500 }}>Semantic Search</span>
          </nav>
        </div>

        <div className="page-body" style={{ maxWidth: "800px" }}>
          {/* Header */}
          <div style={{ marginBottom: "1.5rem" }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: "0 0 0.25rem" }}>
              Semantic Code & Symbol Search
            </h1>
            <p className="text-sm text-muted">
              Hybrid retrieval combining AST symbol matching and vector semantic search.
            </p>
          </div>

          {/* Search Bar */}
          <form onSubmit={handleSearch} style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem" }}>
            <input
              className="input"
              placeholder="Search by keyword, function name, docstring, or natural language query…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              style={{ flex: 1 }}
              autoFocus
            />
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? "Searching…" : "Search"}
            </button>
          </form>

          {/* Results List */}
          {loading ? (
            <p className="text-sm text-muted">Searching repository index…</p>
          ) : hasSearched && results.length === 0 ? (
            <div className="card">
              <div className="empty-state">
                <p>No code matches found for &quot;{query}&quot;</p>
              </div>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "0.875rem" }}>
              {results.map((item, idx) => (
                <div key={idx} className="card" style={{ padding: "1rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.375rem" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span className="font-mono text-sm" style={{ fontWeight: 600 }}>{item.file_path}</span>
                      <span className="text-xs text-muted font-mono">:{item.line_start}</span>
                    </div>

                    <div style={{ display: "flex", gap: "0.375rem" }}>
                      <span className={`badge ${item.source === "hybrid" ? "badge-success" : item.source === "vector" ? "badge-pending" : "badge-default"}`}>
                        {item.source}
                      </span>
                      {item.rrf_score && (
                        <span className="badge badge-default">Score: {item.rrf_score}</span>
                      )}
                    </div>
                  </div>

                  {item.name && (
                    <div className="text-xs text-muted" style={{ marginBottom: "0.375rem" }}>
                      Symbol: <strong>{item.name}</strong> ({item.type})
                    </div>
                  )}

                  <pre className="font-mono text-xs" style={{
                    background: "#0f172a", color: "#f8fafc", padding: "0.625rem 0.75rem",
                    borderRadius: "var(--radius)", overflowX: "auto", margin: 0, whiteSpace: "pre-wrap"
                  }}>
                    {item.content}
                  </pre>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
