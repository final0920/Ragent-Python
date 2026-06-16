import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import KnowledgePage from "./pages/KnowledgePage";
import IntentPage from "./pages/IntentPage";

export default function App() {
  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">Ragent</div>
        <nav>
          <NavLink to="/chat" className={({ isActive }) => (isActive ? "active" : "")}>智能问答</NavLink>
          <NavLink to="/knowledge" className={({ isActive }) => (isActive ? "active" : "")}>知识库</NavLink>
          <NavLink to="/intent" className={({ isActive }) => (isActive ? "active" : "")}>意图树</NavLink>
        </nav>
        <div className="sidebar-foot">RAG · FastAPI + LangGraph</div>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<Navigate to="/chat" replace />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/intent" element={<IntentPage />} />
        </Routes>
      </main>
    </div>
  );
}
