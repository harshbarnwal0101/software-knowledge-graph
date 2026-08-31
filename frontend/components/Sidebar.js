"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const NAV = [
  { href: "/dashboard", label: "Dashboard", icon: "⊞" },
  { href: "/repositories", label: "Repositories", icon: "⬡" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const logout = () => {
    localStorage.removeItem("skg_token");
    router.push("/login");
  };

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div style={{
          width: "1.5rem", height: "1.5rem", background: "#18181b",
          borderRadius: "5px", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0
        }}>
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none">
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
        <span style={{ fontWeight: 600, fontSize: "0.875rem" }}>CodeGraph</span>
      </div>

      <nav className="sidebar-nav">
        {NAV.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`sidebar-nav-item ${pathname === item.href ? "active" : ""}`}
          >
            <span style={{ fontSize: "0.875rem", opacity: 0.7 }}>{item.icon}</span>
            {item.label}
          </Link>
        ))}
      </nav>

      <div style={{ padding: "0.75rem 0.5rem", borderTop: "1px solid var(--border)" }}>
        <button onClick={logout} className="sidebar-nav-item" style={{ width: "100%", background: "none", border: "none", cursor: "pointer" }}>
          <span style={{ fontSize: "0.875rem", opacity: 0.7 }}>→</span>
          Sign out
        </button>
      </div>
    </aside>
  );
}
