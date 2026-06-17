import { useEffect, useState } from "react";
import { api, type KnowledgeBase } from "../api";

export default function IngestionPage() {
  const [pipes, setPipes] = useState<{ id: string; name: string }[]>([]);
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [name, setName] = useState("");
  const [pid, setPid] = useState("");
  const [kbId, setKbId] = useState("");
  const [text, setText] = useState("");
  const [msg, setMsg] = useState("");

  const load = () => { api.listPipelines().then(setPipes).catch(() => {}); api.listKnowledgeBases().then(setKbs).catch(() => {}); };
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!name.trim()) return;
    // 默认节点链:source -> chunk(结构感知) -> index
    await api.createPipeline(name.trim(), [
      { node_type: "source", settings: { source_type: "text" } },
      { node_type: "chunk", settings: { strategy: "structure_aware" } },
      { node_type: "index", settings: {} },
    ]);
    setName(""); load();
  };

  const run = async () => {
    if (!pid || !kbId || !text.trim()) { setMsg("请选择流水线、知识库并填入文本"); return; }
    setMsg("运行中…");
    const r = await api.runPipeline(pid, kbId, text);
    setMsg(r.status === "done" ? `完成:${r.chunk_count} 块` : `失败:${r.error || ""}`);
  };

  return (
    <div className="page">
      <h1>摄取流水线</h1>
      <div className="card">
        <div className="row">
          <input type="text" placeholder="新建流水线名称" value={name} onChange={(e) => setName(e.target.value)} />
          <button onClick={create}>新建(source→chunk→index)</button>
        </div>
      </div>
      <div className="card">
        <div className="row" style={{ marginBottom: 10 }}>
          <select value={pid} onChange={(e) => setPid(e.target.value)} style={{ padding: 10, borderRadius: 8 }}>
            <option value="">选择流水线…</option>
            {pipes.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <select value={kbId} onChange={(e) => setKbId(e.target.value)} style={{ padding: 10, borderRadius: 8 }}>
            <option value="">选择知识库…</option>
            {kbs.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
          </select>
          <button onClick={run}>运行</button>
        </div>
        <textarea placeholder="粘贴要摄取的文本" value={text} onChange={(e) => setText(e.target.value)} style={{ width: "100%", minHeight: 120 }} />
        {msg && <div className="muted" style={{ marginTop: 8 }}>{msg}</div>}
      </div>
    </div>
  );
}
