"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { repoApi } from "@/lib/api";

export default function NewRepositoryPage() {
  const router = useRouter();
  const [form, setForm] = useState({ github_url: "", name: "", description: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await repoApi.create(form);
      router.push(`/repositories/${res.data.id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Failed to add repository.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div className="topnav">
          <nav style={{ fontSize: "0.875rem", color: "var(--muted-foreground)", display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <Link href="/repositories" style={{ color: "inherit", textDecoration: "none" }}>Repositories</Link>
            <span>/</span>
            <span style={{ color: "var(--foreground)" }}>New</span>
          </nav>
        </div>

        <div className="page-body" style={{ maxWidth: "600px" }}>
          <div style={{ marginBottom: "1.5rem" }}>
            <h1 style={{ fontSize: "1.125rem", fontWeight: 600, margin: 0 }}>Add Repository</h1>
            <p className="text-muted text-sm" style={{ marginTop: "0.25rem" }}>
              Connect a GitHub repository to start building its knowledge graph.
            </p>
          </div>

          <div className="card" style={{ padding: "1.5rem" }}>
            <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1.125rem" }}>
              <div>
                <label className="label">GitHub URL <span style={{ color: "var(--destructive)" }}>*</span></label>
                <input
                  type="url"
                  className="input"
                  placeholder="https://github.com/owner/repository"
                  value={form.github_url}
                  onChange={(e) => setForm({ ...form, github_url: e.target.value })}
                  required
                />
                <p className="text-xs text-muted" style={{ marginTop: "0.3rem" }}>Public repositories only in Phase 1.</p>
              </div>

              <div>
                <label className="label">Name <span className="text-xs text-muted">(optional)</span></label>
                <input
                  type="text"
                  className="input"
                  placeholder="Leave blank to use repository name"
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                />
              </div>

              <div>
                <label className="label">Description <span className="text-xs text-muted">(optional)</span></label>
                <textarea
                  className="input"
                  rows={3}
                  placeholder="Brief description of this repository"
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                />
              </div>

              {error && (
                <div style={{
                  padding: "0.625rem 0.75rem", background: "#fee2e2",
                  border: "1px solid #fecaca", borderRadius: "var(--radius)",
                  fontSize: "0.875rem", color: "#991b1b"
                }}>
                  {error}
                </div>
              )}

              <div style={{ display: "flex", gap: "0.75rem", paddingTop: "0.25rem" }}>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? "Adding…" : "Add Repository"}
                </button>
                <Link href="/repositories" className="btn btn-secondary">Cancel</Link>
              </div>
            </form>
          </div>

          {/* Phase note */}
          <div style={{
            marginTop: "1rem", padding: "0.875rem 1rem",
            background: "var(--muted)", borderRadius: "var(--radius)",
            fontSize: "0.8125rem", color: "var(--muted-foreground)",
            border: "1px solid var(--border)"
          }}>
            <strong style={{ color: "var(--foreground)" }}>Phase 1</strong> — Repository registration is live.
            Full analysis (parsing, graph building, embeddings) is coming in Phase 2.
          </div>
        </div>
      </main>
    </div>
  );
}
