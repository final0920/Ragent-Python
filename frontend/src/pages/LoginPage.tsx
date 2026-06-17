import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../stores/auth";

export default function LoginPage() {
  const login = useAuth((s) => s.login);
  const nav = useNavigate();
  const [u, setU] = useState("admin");
  const [p, setP] = useState("admin");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async () => {
    setBusy(true); setErr("");
    try { await login(u, p); nav("/chat"); }
    catch (e) { setErr("登录失败:" + String(e)); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center" }}>
      <div className="card" style={{ width: 340 }}>
        <h1 style={{ marginTop: 0 }}>Ragent 登录</h1>
        <div style={{ display: "grid", gap: 10 }}>
          <input type="text" placeholder="用户名" value={u} onChange={(e) => setU(e.target.value)} />
          <input type="text" placeholder="密码" value={p} onChange={(e) => setP(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") void submit(); }} />
          <button onClick={submit} disabled={busy}>{busy ? "登录中…" : "登录"}</button>
          {err && <div style={{ color: "var(--warn,#ff7b72)" }}>{err}</div>}
          <div className="muted">默认 admin / admin</div>
        </div>
      </div>
    </div>
  );
}
