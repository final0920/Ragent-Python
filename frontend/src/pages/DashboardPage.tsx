import { useEffect, useState } from "react";
import { api } from "../api";

const LABELS: Record<string, string> = {
  conversations: "会话", messages: "消息", knowledge_bases: "知识库",
  documents: "文档", chunks: "分块", feedback_up: "点赞", feedback_down: "点踩",
};

export default function DashboardPage() {
  const [data, setData] = useState<Record<string, number>>({});
  const [err, setErr] = useState("");
  useEffect(() => { api.dashboard().then(setData).catch((e) => setErr(String(e))); }, []);
  return (
    <div className="page">
      <h1>概览</h1>
      {err && <div className="card muted">{err}</div>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(150px,1fr))", gap: 12 }}>
        {Object.entries(LABELS).map(([k, label]) => (
          <div className="card" key={k} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 28, fontWeight: 800, color: "var(--accent)" }}>{data[k] ?? "-"}</div>
            <div className="muted">{label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
