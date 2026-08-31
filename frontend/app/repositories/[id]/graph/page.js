"use client";
import { useEffect, useState, useCallback, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import api, { repoApi } from "@/lib/api";

import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// ── Custom Node Components ─────────────────────────────────────

const NODE_COLORS = {
  File:     { bg: "#1e293b", border: "#475569", text: "#f8fafc", tagBg: "#334155", tagText: "#94a3b8" },
  Class:    { bg: "#1e1b4b", border: "#4338ca", text: "#e0e7ff", tagBg: "#312e81", tagText: "#a5b4fc" },
  Function: { bg: "#064e3b", border: "#059669", text: "#ecfdf5", tagBg: "#065f46", tagText: "#6ee7b7" },
  Method:   { bg: "#3b0764", border: "#7c3aed", text: "#f5f3ff", tagBg: "#581c87", tagText: "#c4b5fd" },
  Import:   { bg: "#451a03", border: "#d97706", text: "#fffbeb", tagBg: "#78350f", tagText: "#fde68a" },
};

function CustomNode({ data, selected }) {
  const nodeType = data.nodeType || "File";
  const colors = NODE_COLORS[nodeType] || NODE_COLORS.File;

  return (
    <div
      style={{
        background: colors.bg,
        border: `1.5px solid ${selected ? "#38bdf8" : colors.border}`,
        boxShadow: selected ? "0 0 0 3px rgba(56, 189, 248, 0.3)" : "0 2px 4px rgba(0,0,0,0.2)",
        borderRadius: "8px",
        padding: "8px 12px",
        minWidth: "140px",
        color: colors.text,
        fontSize: "12px",
        fontFamily: "Inter, sans-serif",
        cursor: "pointer",
        transition: "all 0.15s ease",
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: colors.border, width: 6, height: 6 }} />

      <div style={{ display: "flex", alignItems: "center", justifyBetween: "space-between", gap: "6px" }}>
        <span style={{ fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "160px" }}>
          {data.label}
        </span>
        <span
          style={{
            background: colors.tagBg,
            color: colors.tagText,
            fontSize: "9px",
            fontWeight: 600,
            padding: "1px 5px",
            borderRadius: "4px",
            textTransform: "uppercase",
          }}
        >
          {nodeType}
        </span>
      </div>

      {data.path && (
        <div style={{ fontSize: "10px", opacity: 0.7, marginTop: "2px", fontFamily: "monospace", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", maxWidth: "160px" }}>
          {data.path}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: colors.border, width: 6, height: 6 }} />
    </div>
  );
}

const nodeTypes = {
  file: CustomNode,
  class: CustomNode,
  function: CustomNode,
  method: CustomNode,
  import: CustomNode,
  symbol: CustomNode,
};

// ── Graph Layout Helper ────────────────────────────────────────

function autoLayoutNodes(rawNodes) {
  // Grid / ring layout algorithm for nodes
  const cols = Math.ceil(Math.sqrt(rawNodes.length));
  return rawNodes.map((n, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    return {
      ...n,
      position: {
        x: col * 200 + (row % 2 === 0 ? 0 : 30),
        y: row * 100,
      },
    };
  });
}

// ── Main Graph Page ────────────────────────────────────────────

export default function GraphExplorerPage() {
  const { id } = useParams();
  const router = useRouter();

  const [repo, setRepo] = useState(null);
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNode, setSelectedNode] = useState(null);
  const [search, setSearch] = useState("");
  const [filterType, setFilterType] = useState("ALL");
  const [loading, setLoading] = useState(true);

  // Load Graph Data
  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }

    Promise.all([
      repoApi.get(id),
      api.get(`/api/repositories/${id}/graph?limit=150`)
    ])
      .then(([repoRes, graphRes]) => {
        setRepo(repoRes.data);
        const layoutedNodes = autoLayoutNodes(graphRes.data.nodes || []);
        setNodes(layoutedNodes);
        setEdges(graphRes.data.edges || []);
      })
      .catch((err) => console.error("Failed to load graph:", err))
      .finally(() => setLoading(false));
  }, [id, router, setNodes, setEdges]);

  // Handle Node Click
  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node);
  }, []);

  // Filtered Nodes & Edges
  const filteredNodes = useMemo(() => {
    return nodes.map((node) => {
      const matchesSearch = !search || node.data.label.toLowerCase().includes(search.toLowerCase());
      const matchesType = filterType === "ALL" || node.data.nodeType === filterType;
      const isHidden = !matchesSearch || !matchesType;

      return {
        ...node,
        hidden: isHidden,
      };
    });
  }, [nodes, search, filterType]);

  if (loading) return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content">
        <div style={{ padding: "2rem", color: "var(--muted-foreground)", fontSize: "0.875rem" }}>Loading knowledge graph…</div>
      </main>
    </div>
  );

  return (
    <div className="page-layout">
      <Sidebar />
      <main className="page-content" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
        {/* Topnav */}
        <div className="topnav">
          <nav className="text-sm text-muted" style={{ display: "flex", alignItems: "center", gap: "0.375rem" }}>
            <Link href="/repositories" style={{ color: "inherit", textDecoration: "none" }}>Repositories</Link>
            <span>/</span>
            <Link href={`/repositories/${id}`} style={{ color: "inherit", textDecoration: "none" }}>{repo?.name}</Link>
            <span>/</span>
            <span style={{ color: "var(--foreground)", fontWeight: 500 }}>Graph Explorer</span>
          </nav>
        </div>

        {/* Toolbar */}
        <div style={{
          padding: "0.75rem 1rem", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", gap: "0.75rem", background: "var(--card)"
        }}>
          {/* Search Box */}
          <input
            className="input"
            placeholder="Search nodes by name…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ maxWidth: "240px", height: "1.875rem", fontSize: "0.8125rem" }}
          />

          {/* Type Filter Buttons */}
          <div style={{ display: "flex", gap: "0.25rem" }}>
            {["ALL", "File", "Class", "Function", "Method"].map((type) => (
              <button
                key={type}
                onClick={() => setFilterType(type)}
                className={`btn btn-sm ${filterType === type ? "btn-primary" : "btn-ghost"}`}
                style={{ fontSize: "0.75rem", padding: "0 0.5rem" }}
              >
                {type}
              </button>
            ))}
          </div>

          <div style={{ flex: 1 }} />

          <span className="text-xs text-muted">
            {nodes.filter(n => !n.hidden).length} of {nodes.length} nodes
          </span>
        </div>

        {/* Main Canvas Area */}
        <div style={{ flex: 1, display: "flex", position: "relative" }}>
          <div style={{ flex: 1, height: "100%", background: "#0b0f19" }}>
            <ReactFlow
              nodes={filteredNodes}
              edges={edges}
              nodeTypes={nodeTypes}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              colorMode="dark"
            >
              <Background color="#1e293b" gap={16} size={1} />
              <Controls style={{ background: "#1e293b", border: "1px solid #334155", color: "white" }} />
              <MiniMap style={{ background: "#0f172a" }} nodeColor="#38bdf8" />
            </ReactFlow>
          </div>

          {/* Right Side Detail Panel */}
          {selectedNode && (
            <aside style={{
              width: "320px", borderLeft: "1px solid var(--border)",
              background: "var(--card)", padding: "1.25rem", overflowY: "auto"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <span className="badge badge-default">{selectedNode.data.nodeType || "Node"}</span>
                <button className="btn btn-ghost btn-sm" onClick={() => setSelectedNode(null)}>✕</button>
              </div>

              <h3 style={{ fontSize: "1.125rem", fontWeight: 600, margin: "0 0 0.5rem", wordBreak: "break-all" }}>
                {selectedNode.data.label}
              </h3>

              {selectedNode.data.path && (
                <div style={{ marginBottom: "1rem" }}>
                  <label className="text-xs text-muted" style={{ display: "block", marginBottom: "2px" }}>File Path</label>
                  <div className="font-mono text-xs" style={{ background: "var(--muted)", padding: "4px 8px", borderRadius: "4px", wordBreak: "break-all" }}>
                    {selectedNode.data.path}
                    {selectedNode.data.line ? `:${selectedNode.data.line}` : ""}
                  </div>
                </div>
              )}

              {selectedNode.data.signature && (
                <div style={{ marginBottom: "1rem" }}>
                  <label className="text-xs text-muted" style={{ display: "block", marginBottom: "2px" }}>Signature</label>
                  <pre className="font-mono text-xs" style={{ background: "var(--muted)", padding: "6px 8px", borderRadius: "4px", overflowX: "auto" }}>
                    {selectedNode.data.signature}
                  </pre>
                </div>
              )}

              <hr />

              <div style={{ marginTop: "1rem" }}>
                <h4 style={{ fontSize: "0.8125rem", fontWeight: 600, marginBottom: "0.5rem" }}>Connected Edges</h4>
                {edges.filter(e => e.source === selectedNode.id || e.target === selectedNode.id).map(e => (
                  <div key={e.id} style={{ fontSize: "0.75rem", padding: "4px 0", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between" }}>
                    <span className="text-muted">{e.source === selectedNode.id ? "→ " + e.label : "← " + e.label}</span>
                    <span className="font-mono">{e.source === selectedNode.id ? e.target.replace("sym_","").replace("file_","") : e.source.replace("sym_","").replace("file_","")}</span>
                  </div>
                ))}
              </div>
            </aside>
          )}
        </div>
      </main>
    </div>
  );
}
