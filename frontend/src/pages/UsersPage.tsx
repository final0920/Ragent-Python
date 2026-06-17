import { useEffect, useState } from "react";
import { api } from "../api";

export default function UsersPage() {
  const [rows, setRows] = useState<{ id: string; username: string; role: string }[]>([]);
  const [u, setU] = useState("");
  const [p, setP] = useState("");
  const [role, setRole] = useState("user");
  const [msg, setMsg] = useState("");
  const load = () => api.listUsers().then(setRows).catch((e) => setMsg(String(e)));
  useEffect(() => { load(); }, []);
  const add = async () => {
    if (!u.trim() || !p.trim()) return;
    try { await api.createUser(u.trim(), p.trim(), role); setU(""); setP(""); load(); }
    catch (e) { setMsg(String(e)); }
  };
  const del = async (id: string) => { await api.deleteUser(id); load(); };
  return (
    <div className="page">
      <h1>用户管理</h1>
      <div className="card">
        <div className="row">
          <input type="text" placeholder="用户名" value={u} onChange={(e) => setU(e.target.value)} />
          <input type="text" placeholder="密码" value={p} onChange={(e) => setP(e.target.value)} />
          <select value={role} onChange={(e) => setRole(e.target.value)} style={{ padding: 10, borderRadius: 8 }}>
            <option value="user">user</option>
            <option value="admin">admin</option>
          </select>
          <button onClick={add}>新增用户</button>
        </div>
      </div>
      {msg && <div className="card muted">{msg}</div>}
      <div className="card">
        <table>
          <thead><tr><th>用户名</th><th>角色</th><th></th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}><td>{r.username}</td><td>{r.role}</td>
                <td><button className="ghost" onClick={() => del(r.id)}>删除</button></td></tr>
            ))}
            {rows.length === 0 && <tr><td colSpan={3} className="muted">暂无用户</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}
