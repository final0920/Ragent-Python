import { useEffect, useState } from "react";
import { api, type IntentNode } from "../api";

const KIND_LABEL: Record<number, string> = { 0: "KB", 1: "SYSTEM", 2: "MCP" };

export default function IntentPage() {
  const [nodes, setNodes] = useState<IntentNode[]>([]);
  const [form, setForm] = useState({ intent_code: "", name: "", description: "", kind: 0, collection_name: "" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    try { setNodes(await api.listIntents()); } catch (e) { setMsg(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const create = async () => {
    if (!form.intent_code.trim() || !form.name.trim()) { setMsg("intent_code 与 name 必填"); return; }
    setBusy(true);
    try {
      await api.createIntent({ ...form, level: 2 });
      setForm({ intent_code: "", name: "", description: "", kind: 0, collection_name: "" });
      await load();
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };

  return (
    <div className="page">
      <h1>意图树管理</h1>
      <div className="card">
        <div className="row" style={{ marginBottom: 10 }}>
          <input type="text" placeholder="intent_code" value={form.intent_code} onChange={(e) => setForm({ ...form, intent_code: e.target.value })} />
          <input type="text" placeholder="名称" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </div>
        <div className="row" style={{ marginBottom: 10 }}>
          <input type="text" placeholder="说明(可选)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
        </div>
        <div className="row">
          <select value={form.kind} onChange={(e) => setForm({ ...form, kind: Number(e.target.value) })} style={{ padding: 10, borderRadius: 8 }}>
            <option value={0}>KB</option>
            <option value={1}>SYSTEM</option>
            <option value={2}>MCP</option>
          </select>
          <input type="text" placeholder="collection_name (KB 类填)" value={form.collection_name} onChange={(e) => setForm({ ...form, collection_name: e.target.value })} />
          <button onClick={create} disabled={busy}>新增叶子意图</button>
        </div>
        <div className="muted" style={{ marginTop: 8 }}>叶子意图(level=2)参与 LLM 打分；KB 类命中其 collection 做定向检索。</div>
      </div>
      {msg && <div className="card muted">{msg}</div>}
      <div className="card">
        <table>
          <thead><tr><th>code</th><th>名称</th><th>kind</th><th>collection</th><th>启用</th></tr></thead>
          <tbody>
            {nodes.map((n) => (
              <tr key={n.id}>
                <td>{n.intent_code}</td><td>{n.name}</td>
                <td><span className="tag">{KIND_LABEL[n.kind] ?? n.kind}</span></td>
                <td className="muted">{n.collection_name || "-"}</td>
                <td>{n.enabled ? "是" : "否"}</td>
              </tr>
            ))}
            {nodes.length === 0 && <tr><td colSpan={5} className="muted">暂无意图节点</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
