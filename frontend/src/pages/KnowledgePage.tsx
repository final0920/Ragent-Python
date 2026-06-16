import { useEffect, useRef, useState } from "react";
import { api, type KnowledgeBase } from "../api";

export default function KnowledgePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [target, setTarget] = useState("");

  const load = async () => {
    try { setKbs(await api.listKnowledgeBases()); } catch (e) { setMsg(String(e)); }
  };
  useEffect(() => { void load(); }, []);

  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try { await api.createKnowledgeBase(name.trim()); setName(""); await load(); }
    catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };

  const upload = async () => {
    const f = fileRef.current?.files?.[0];
    if (!f || !target) { setMsg("请选择知识库与文件"); return; }
    setBusy(true); setMsg("上传中…");
    try {
      const r = await api.uploadDoc(target, f);
      setMsg(`上传完成：${r.chunk_count} 个分块`);
      if (fileRef.current) fileRef.current.value = "";
      await load();
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };

  return (
    <div className="page">
      <h1>知识库管理</h1>
      <div className="card">
        <div className="row">
          <input type="text" placeholder="新建知识库名称" value={name} onChange={(e) => setName(e.target.value)} />
          <button onClick={create} disabled={busy}>新建</button>
        </div>
      </div>
      <div className="card">
        <div className="row">
          <select value={target} onChange={(e) => setTarget(e.target.value)} style={{ padding: 10, borderRadius: 8 }}>
            <option value="">选择知识库…</option>
            {kbs.map((k) => <option key={k.id} value={k.id}>{k.name}</option>)}
          </select>
          <input type="file" ref={fileRef} accept=".txt,.md,.pdf" />
          <button onClick={upload} disabled={busy}>上传文档</button>
        </div>
        <div className="muted" style={{ marginTop: 8 }}>支持 .txt / .md / .pdf</div>
      </div>
      {msg && <div className="card muted">{msg}</div>}
      <div className="card">
        <table>
          <thead><tr><th>名称</th><th>collection</th><th>id</th></tr></thead>
          <tbody>
            {kbs.map((k) => <tr key={k.id}><td>{k.name}</td><td>{k.collection_name}</td><td className="muted">{k.id}</td></tr>)}
            {kbs.length === 0 && <tr><td colSpan={3} className="muted">暂无知识库</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
