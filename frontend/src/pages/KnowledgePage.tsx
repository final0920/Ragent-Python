import { useEffect, useRef, useState } from "react";
import { api, type ChunkItem, type DocItem, type KnowledgeBase } from "../api";

export default function KnowledgePage() {
  const [kbs, setKbs] = useState<KnowledgeBase[]>([]);
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const [target, setTarget] = useState("");
  const [strategy, setStrategy] = useState("fixed_size");
  const [docs, setDocs] = useState<DocItem[]>([]);
  const [chunks, setChunks] = useState<ChunkItem[]>([]);
  const [chunkDoc, setChunkDoc] = useState("");

  const loadKbs = async () => { try { setKbs(await api.listKnowledgeBases()); } catch (e) { setMsg(String(e)); } };
  const loadDocs = async (kbId: string) => { if (!kbId) { setDocs([]); return; } try { setDocs((await api.listDocs(kbId)).items); } catch { setDocs([]); } };
  useEffect(() => { void loadKbs(); }, []);
  useEffect(() => { void loadDocs(target); setChunks([]); setChunkDoc(""); }, [target]);

  const create = async () => {
    if (!name.trim()) return;
    setBusy(true);
    try { await api.createKnowledgeBase(name.trim()); setName(""); await loadKbs(); }
    catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };

  const upload = async () => {
    const f = fileRef.current?.files?.[0];
    if (!f || !target) { setMsg("请选择知识库与文件"); return; }
    setBusy(true); setMsg("上传中…");
    try {
      const r = await api.uploadDoc(target, f, strategy);
      setMsg(`上传完成:${r.chunk_count} 个分块`);
      if (fileRef.current) fileRef.current.value = "";
      await loadDocs(target);
    } catch (e) { setMsg(String(e)); } finally { setBusy(false); }
  };

  const delDoc = async (id: string) => { await api.deleteDoc(id); await loadDocs(target); if (chunkDoc === id) setChunks([]); };
  const viewChunks = async (id: string) => { setChunkDoc(id); setChunks(await api.listChunks(id)); };
  const delChunk = async (id: string) => { await api.deleteChunk(id); if (chunkDoc) setChunks(await api.listChunks(chunkDoc)); };

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
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)} style={{ padding: 10, borderRadius: 8 }}>
            <option value="fixed_size">定长分块</option>
            <option value="structure_aware">结构感知分块</option>
          </select>
          <input type="file" ref={fileRef} accept=".txt,.md,.pdf" />
          <button onClick={upload} disabled={busy}>上传文档</button>
        </div>
        <div className="muted" style={{ marginTop: 8 }}>支持 .txt / .md / .pdf</div>
      </div>
      {msg && <div className="card muted">{msg}</div>}

      {target && (
        <div className="card">
          <h3>文档列表</h3>
          <table>
            <thead><tr><th>名称</th><th>状态</th><th>分块数</th><th>策略</th><th></th></tr></thead>
            <tbody>
              {docs.map((d) => (
                <tr key={d.id}>
                  <td>{d.doc_name}</td><td>{d.status}</td><td>{d.chunk_count}</td><td>{d.chunk_strategy}</td>
                  <td>
                    <button className="ghost" onClick={() => viewChunks(d.id)}>分块</button>{" "}
                    <button className="ghost" onClick={() => delDoc(d.id)}>删除</button>
                  </td>
                </tr>
              ))}
              {docs.length === 0 && <tr><td colSpan={5} className="muted">该库暂无文档</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {chunkDoc && (
        <div className="card">
          <h3>分块({chunks.length})</h3>
          <table>
            <thead><tr><th>#</th><th>内容</th><th>字数</th><th></th></tr></thead>
            <tbody>
              {chunks.map((c) => (
                <tr key={c.id}>
                  <td>{c.chunk_index}</td><td>{c.content.slice(0, 80)}</td><td>{c.char_count}</td>
                  <td><button className="ghost" onClick={() => delChunk(c.id)}>删除</button></td>
                </tr>
              ))}
              {chunks.length === 0 && <tr><td colSpan={4} className="muted">无分块</td></tr>}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
