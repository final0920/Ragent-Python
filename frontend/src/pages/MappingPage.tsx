import { useEffect, useState } from "react";
import { api, type Mapping } from "../api";

export default function MappingPage() {
  const [rows, setRows] = useState<Mapping[]>([]);
  const [src, setSrc] = useState("");
  const [tgt, setTgt] = useState("");
  const load = () => api.listMappings().then(setRows).catch(() => {});
  useEffect(() => { load(); }, []);
  const add = async () => { if (!src.trim() || !tgt.trim()) return; await api.createMapping(src.trim(), tgt.trim()); setSrc(""); setTgt(""); load(); };
  const del = async (id: string) => { await api.deleteMapping(id); load(); };
  return (
    <div className="page">
      <h1>词典归一化</h1>
      <div className="card">
        <div className="row">
          <input type="text" placeholder="源词(同义/口语)" value={src} onChange={(e) => setSrc(e.target.value)} />
          <input type="text" placeholder="标准词" value={tgt} onChange={(e) => setTgt(e.target.value)} />
          <button onClick={add}>新增</button>
        </div>
        <div className="muted" style={{ marginTop: 8 }}>检索前会把源词替换为标准词,提升召回一致性。</div>
      </div>
      <div className="card">
        <table>
          <thead><tr><th>源词</th><th>标准词</th><th>优先级</th><th></th></tr></thead>
          <tbody>
            {rows.map((m) => (
              <tr key={m.id}><td>{m.source_term}</td><td>{m.target_term}</td><td>{m.priority}</td>
                <td><button className="ghost" onClick={() => del(m.id)}>删除</button></td></tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={4} className="muted">暂无映射</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
