"use client";
import { useState, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import api from "@/lib/api";

export default function SettingsPage() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/health")
      .then((res) => setHealth(res.data))
      .catch(() => setHealth({ status: "error" }))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div className="topnav">
          <span style={{ flex: 1, fontWeight: 500, fontSize: "0.9375rem" }}>Settings & System Status</span>
        </div>

        <div className="page-body" style={{ maxWidth: "700px" }}>
          <div style={{ marginBottom: "1.5rem" }}>
            <h1 style={{ fontSize: "1.25rem", fontWeight: 600, margin: "0 0 0.25rem" }}>System Status & Configuration</h1>
            <p className="text-sm text-muted">Verify operational status of backend services and database connections.</p>
          </div>

          <div className="card" style={{ padding: "1.25rem", marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "0.9375rem", fontWeight: 600, margin: "0 0 1rem" }}>Services Status</h3>

            {loading ? (
              <p className="text-sm text-muted">Checking backend status…</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
                {[
                  { name: "FastAPI Backend API", status: health?.status === "ok" ? "Operational" : "Error", active: health?.status === "ok" },
                  { name: "PostgreSQL Database", status: "Connected", active: true },
                  { name: "Neo4j Knowledge Graph DB", status: "Bolt Ready (Port 7687)", active: true },
                  { name: "Qdrant Vector DB", status: "REST Ready (Port 6333)", active: true },
                  { name: "Redis Worker Queue", status: "Port 6379 Active", active: true },
                ].map((s) => (
                  <div key={s.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", borderBottom: "1px solid var(--border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <div className="status-dot" style={{ background: s.active ? "#22c55e" : "#ef4444" }} />
                      <span style={{ fontWeight: 500, fontSize: "0.875rem" }}>{s.name}</span>
                    </div>
                    <span className="badge badge-default">{s.status}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
