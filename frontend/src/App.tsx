import { NavLink, Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./stores/auth";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";
import IntentPage from "./pages/IntentPage";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import IngestionPage from "./pages/IngestionPage";
import TracePage from "./pages/TracePage";
import MappingPage from "./pages/MappingPage";
import SamplePage from "./pages/SamplePage";

function RequireAuth({ children }: { children: JSX.Element }) {
  const token = useAuth((s) => s.token);
  const loc = useLocation();
  if (!token) return <Navigate to="/login" state={{ from: loc }} replace />;
  return children;
}

const NAV = [
  { to: "/chat", label: "智能问答" },
  { to: "/dashboard", label: "概览" },
  { to: "/knowledge", label: "知识库" },
  { to: "/intent", label: "意图树" },
  { to: "/ingestion", label: "摄取流水线" },
  { to: "/trace", label: "Trace" },
  { to: "/mapping", label: "词典" },
  { to: "/sample", label: "示例问题" },
];

function Shell({ children }: { children: JSX.Element }) {
  const { username, logout } = useAuth();
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">Ragent</div>
        <nav>
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} className={({ isActive }) => (isActive ? "active" : "")}>{n.label}</NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div>{username || "未登录"}</div>
          <button className="ghost" style={{ marginTop: 8 }} onClick={logout}>退出</button>
        </div>
      </aside>
      <main className="content">{children}</main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <RequireAuth>
            <Shell>
              <Routes>
                <Route path="/" element={<Navigate to="/chat" replace />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/knowledge" element={<KnowledgePage />} />
                <Route path="/intent" element={<IntentPage />} />
                <Route path="/ingestion" element={<IngestionPage />} />
                <Route path="/trace" element={<TracePage />} />
                <Route path="/mapping" element={<MappingPage />} />
                <Route path="/sample" element={<SamplePage />} />
              </Routes>
            </Shell>
          </RequireAuth>
        }
      />
    </Routes>
  );
}
