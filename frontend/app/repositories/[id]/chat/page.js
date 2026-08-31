"use client";
import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import api, { repoApi } from "@/lib/api";

const SAMPLE_QUESTIONS = [
  "Explain the architecture of this codebase.",
  "Where is authentication implemented?",
  "What classes and functions are defined?",
  "Show the main dependencies of this project.",
];

export default function ChatPage() {
  const { id } = useParams();
  const router = useRouter();

  const [repo, setRepo] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const token = localStorage.getItem("skg_token");
    if (!token) { router.replace("/login"); return; }
    repoApi.get(id).then((res) => setRepo(res.data)).catch(() => router.replace("/repositories"));
  }, [id, router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleSend = async (e, customQuery = null) => {
    e?.preventDefault();
    const query = customQuery || input;
    if (!query.trim() || loading) return;

    const userMsg = { role: "user", content: query };
    setMessages((prev) => [...prev, userMsg]);
    if (!customQuery) setInput("");
    setLoading(true);

    try {
      const res = await api.post(`/api/repositories/${id}/chat`, { question: query });
      const assistantMsg = {
        role: "assistant",
        content: res.data.answer,
        tools: res.data.tools_executed || [],
        citations: res.data.citations || [],
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error communicating with AI agent. Please try again." }
      ]);
    } finally {
      setLoading(false);
    }
  };

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
            <span style={{ color: "var(--foreground)", fontWeight: 500 }}>AI Code Assistant</span>
          </nav>
        </div>

        {/* Chat Messages Container */}
        <div style={{ flex: 1, overflowY: "auto", padding: "1.5rem" }}>
          <div style={{ maxWidth: "800px", margin: "0 auto" }}>

            {messages.length === 0 ? (
              <div style={{ textAlign: "center", paddingTop: "3rem" }}>
                <div style={{
                  width: "2.5rem", height: "2.5rem", background: "var(--primary)",
                  borderRadius: "8px", display: "inline-flex", alignItems: "center",
                  justifyContent: "center", marginBottom: "1rem"
                }}>
                  <span style={{ color: "white", fontSize: "1.25rem" }}>🤖</span>
                </div>
                <h2 style={{ fontSize: "1.125rem", fontWeight: 600, margin: "0 0 0.5rem" }}>
                  Ask CodeGraph AI about {repo?.name || "the repository"}
                </h2>
                <p className="text-sm text-muted" style={{ maxWidth: "480px", margin: "0 auto 1.5rem" }}>
                  Ask questions about architecture, classes, functions, impact analysis, or where specific features are implemented. Answers include clickable source citations.
                </p>

                {/* Sample Prompt Chips */}
                <div style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem", justifyContent: "center" }}>
                  {SAMPLE_QUESTIONS.map((q) => (
                    <button
                      key={q}
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleSend(null, q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
                {messages.map((m, idx) => (
                  <div key={idx} style={{
                    display: "flex", gap: "0.875rem",
                    alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                    maxWidth: m.role === "user" ? "80%" : "100%",
                  }}>
                    {m.role === "assistant" && (
                      <div style={{
                        width: "1.75rem", height: "1.75rem", background: "#18181b",
                        borderRadius: "6px", display: "flex", alignItems: "center",
                        justifyContent: "center", color: "white", fontSize: "0.75rem", flexShrink: 0
                      }}>
                        AI
                      </div>
                    )}

                    <div style={{ flex: 1 }}>
                      {/* Tool Call Badges */}
                      {m.tools && m.tools.length > 0 && (
                        <div style={{ display: "flex", gap: "0.375rem", marginBottom: "0.5rem", flexWrap: "wrap" }}>
                          {m.tools.map((t, i) => (
                            <span key={i} className="badge badge-default font-mono" style={{ fontSize: "0.6875rem" }}>
                              🔧 {t}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Message Body */}
                      <div className="card" style={{
                        padding: "1rem 1.25rem",
                        background: m.role === "user" ? "var(--primary)" : "var(--card)",
                        color: m.role === "user" ? "var(--primary-foreground)" : "var(--foreground)",
                        whiteSpace: "pre-wrap",
                        fontSize: "0.875rem",
                        lineHeight: 1.6,
                      }}>
                        {m.content}
                      </div>

                      {/* Source Citations */}
                      {m.citations && m.citations.length > 0 && (
                        <div style={{ marginTop: "0.5rem", display: "flex", gap: "0.375rem", flexWrap: "wrap" }}>
                          <span className="text-xs text-muted" style={{ alignSelf: "center" }}>Sources:</span>
                          {m.citations.map((c, i) => (
                            <span key={i} className="badge badge-success font-mono" style={{ fontSize: "0.6875rem" }}>
                              📄 {c.label}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {loading && (
                  <div style={{ display: "flex", gap: "0.875rem" }}>
                    <div style={{
                      width: "1.75rem", height: "1.75rem", background: "#18181b",
                      borderRadius: "6px", display: "flex", alignItems: "center",
                      justifyContent: "center", color: "white", fontSize: "0.75rem"
                    }}>
                      AI
                    </div>
                    <div className="card" style={{ padding: "0.75rem 1rem" }}>
                      <span className="text-sm text-muted">Analyzing codebase & generating citations…</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </div>

        {/* Input Bar */}
        <div style={{ padding: "1rem 1.5rem", borderTop: "1px solid var(--border)", background: "var(--card)" }}>
          <form onSubmit={handleSend} style={{ maxWidth: "800px", margin: "0 auto", display: "flex", gap: "0.5rem" }}>
            <input
              className="input"
              placeholder="Ask CodeGraph AI a question about this repository…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={loading}
              style={{ flex: 1 }}
            />
            <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
              Send
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
