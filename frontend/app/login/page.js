"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const res = await authApi.login(form);
      localStorage.setItem("skg_token", res.data.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err.response?.data?.detail || "Login failed. Check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "1.5rem" }}>
          <div style={{
            width: "1.75rem", height: "1.75rem", background: "#18181b",
            borderRadius: "6px", display: "flex", alignItems: "center", justifyContent: "center"
          }}>
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
              <circle cx="4" cy="4" r="2" fill="white" />
              <circle cx="12" cy="4" r="2" fill="white" opacity=".5" />
              <circle cx="4" cy="12" r="2" fill="white" opacity=".5" />
              <circle cx="12" cy="12" r="2" fill="white" />
              <line x1="4" y1="4" x2="12" y2="4" stroke="white" strokeWidth="1" opacity=".4" />
              <line x1="4" y1="4" x2="4" y2="12" stroke="white" strokeWidth="1" opacity=".4" />
              <line x1="12" y1="4" x2="12" y2="12" stroke="white" strokeWidth="1" opacity=".4" />
              <line x1="4" y1="12" x2="12" y2="12" stroke="white" strokeWidth="1" opacity=".4" />
            </svg>
          </div>
          <span style={{ fontWeight: 600, fontSize: "0.9375rem" }}>CodeGraph</span>
        </div>

        <div className="auth-title">Sign in</div>
        <div className="auth-subtitle">Sign in to your CodeGraph account</div>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              required
            />
          </div>
          <div>
            <label className="label">Password</label>
            <input
              type="password"
              className="input"
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
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

          <button type="submit" className="btn btn-primary" disabled={loading} style={{ width: "100%", marginTop: "0.25rem" }}>
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>

        <div style={{ marginTop: "1.25rem", fontSize: "0.875rem", color: "var(--muted-foreground)", textAlign: "center" }}>
          Don&apos;t have an account?{" "}
          <Link href="/register" style={{ color: "var(--foreground)", fontWeight: 500, textDecoration: "underline" }}>
            Sign up
          </Link>
        </div>
      </div>
    </div>
  );
}
