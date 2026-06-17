import { useEffect, useState } from "react";
import { api, type Sample } from "../api";

export default function SamplePage() {
  const [rows, setRows] = useState<Sample[]>([]);
  const [text, setText] = useState("");
  const load = () => api.listSamples().then(setRows).catch(() => {});
  useEffect(() => { load(); }, []);
  const add = async () => { if (!text.trim()) return; await api.createSample(text.trim()); setText(""); load(); };
  const del = async (id: string) => { await api.deleteSample(id); load(); };
  return (
    <div className="page">
      <h1>示例问题</h1>
      <div className="card">
        <div className="row">
          <input type="text" placeholder="新增欢迎页示例问题" value={text} onChange={(e) => setText(e.target.value)} />
          <button onClick={add}>新增</button>
        </div>
      </div>
      <div className="card">
        <table>
          <thead><tr><th>内容</th><th>启用</th><th></th></tr></thead>
          <tbody>
            {rows.map((s) => (
              <tr key={s.id}><td>{s.content}</td><td>{s.enabled ? "是" : "否"}</td>
                <td><button className="ghost" onClick={() => del(s.id)}>删除</button></td></tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={3} className="muted">暂无示例问题</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
