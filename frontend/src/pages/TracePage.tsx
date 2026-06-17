import { useEffect, useState } from "react";
import { api, type TraceRun } from "../api";

export default function TracePage() {
  const [runs, setRuns] = useState<TraceRun[]>([]);
  const [detail, setDetail] = useState<{ trace_id: string; nodes: { node_type: string; duration_ms: number }[] } | null>(null);
  useEffect(() => { api.listTraces().then(setRuns).catch(() => {}); }, []);
  const open = async (tid: string) => { setDetail(await api.getTrace(tid)); };
  return (
    <div className="page">
      <h1>Trace 全链路</h1>
      <div className="card">
        <table>
          <thead><tr><th>问题</th><th>总耗时(ms)</th><th>状态</th><th></th></tr></thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.trace_id}>
                <td>{r.question.slice(0, 40)}</td><td>{r.total_ms}</td><td>{r.status}</td>
                <td><button className="ghost" onClick={() => open(r.trace_id)}>详情</button></td>
              </tr>
            ))}
            {runs.length === 0 && <tr><td colSpan={4} className="muted">暂无 trace(发起一次问答后产生)</td></tr>}
          </tbody>
        </table>
      </div>
      {detail && (
        <div className="card">
          <h3>各阶段耗时 · {detail.trace_id.slice(0, 8)}</h3>
          <table>
            <thead><tr><th>阶段</th><th>耗时(ms)</th></tr></thead>
            <tbody>{detail.nodes.map((n, i) => <tr key={i}><td>{n.node_type}</td><td>{n.duration_ms}</td></tr>)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
}
