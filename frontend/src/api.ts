// 后端 REST 封装。base 由 Vite 代理到 9090。自动附带 JWT。
const BASE = "/api/ragent";

export function getToken(): string {
  return localStorage.getItem("token") || "";
}
export function setToken(t: string): void {
  if (t) localStorage.setItem("token", t);
  else localStorage.removeItem("token");
}

async function http<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const tok = getToken();
  if (tok) headers.set("Authorization", `Bearer ${tok}`);
  const resp = await fetch(BASE + path, { ...init, headers });
  if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
  const ct = resp.headers.get("content-type") || "";
  return (ct.includes("json") ? await resp.json() : await resp.text()) as T;
}

export interface KnowledgeBase { id: string; name: string; collection_name: string }
export interface DocItem { id: string; doc_name: string; status: string; chunk_count: number; chunk_strategy: string; source_type: string; schedule_enabled: boolean }
export interface ChunkItem { id: string; chunk_index: number; content: string; char_count: number; enabled: boolean }
export interface IntentNode { id: string; intent_code: string; name: string; level: number; kind: number; collection_name: string; enabled: boolean }
export interface TraceRun { trace_id: string; question: string; total_ms: number; status: string }
export interface Mapping { id: string; source_term: string; target_term: string; domain: string; priority: number; enabled: boolean }
export interface Sample { id: string; content: string; enabled: boolean }

export const api = {
  login: (username: string, password: string) =>
    http<{ token: string; username: string; role: string }>("/auth/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    }),
  me: () => http<{ username: string; role: string }>("/user/me"),

  // 知识库 / 文档 / 分块
  listKnowledgeBases: () => http<KnowledgeBase[]>("/knowledge-base"),
  createKnowledgeBase: (name: string) =>
    http<KnowledgeBase>("/knowledge-base", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name }) }),
  listDocs: (kbId: string) => http<{ total: number; items: DocItem[] }>(`/knowledge-base/${kbId}/docs`),
  deleteDoc: (docId: string) => http(`/knowledge-base/docs/${docId}`, { method: "DELETE" }),
  listChunks: (docId: string) => http<ChunkItem[]>(`/knowledge-base/docs/${docId}/chunks`),
  deleteChunk: (chunkId: string) => http(`/knowledge-base/chunks/${chunkId}`, { method: "DELETE" }),
  uploadDoc: (kbId: string, file: File, strategy = "fixed_size") => {
    const fd = new FormData(); fd.append("file", file);
    return http<{ doc_id: string; chunk_count: number }>(`/knowledge-base/${kbId}/docs/upload?strategy=${strategy}`, { method: "POST", body: fd });
  },

  // 意图
  listIntents: () => http<IntentNode[]>("/intent-tree"),
  createIntent: (body: Record<string, unknown>) =>
    http("/intent-tree", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),

  // 摄取流水线
  listPipelines: () => http<{ id: string; name: string }[]>("/ingestion/pipelines"),
  createPipeline: (name: string, nodes: { node_type: string; settings: Record<string, unknown> }[]) =>
    http("/ingestion/pipelines", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name, nodes }) }),
  runPipeline: (pid: string, kb_id: string, text: string) =>
    http<{ status: string; chunk_count?: number; error?: string }>(`/ingestion/pipelines/${pid}/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ kb_id, text }) }),

  // Trace / Dashboard
  listTraces: () => http<TraceRun[]>("/rag/traces/runs"),
  getTrace: (tid: string) => http<{ trace_id: string; question: string; total_ms: number; nodes: { node_type: string; duration_ms: number }[] }>(`/rag/traces/runs/${tid}`),
  dashboard: () => http<Record<string, number>>("/admin/dashboard/overview"),

  // 词典 / 示例问
  listMappings: () => http<Mapping[]>("/mappings"),
  createMapping: (source_term: string, target_term: string) =>
    http("/mappings", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ source_term, target_term }) }),
  deleteMapping: (id: string) => http(`/mappings/${id}`, { method: "DELETE" }),
  listSamples: () => http<Sample[]>("/sample-questions"),
  createSample: (content: string) =>
    http("/sample-questions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) }),
  deleteSample: (id: string) => http(`/sample-questions/${id}`, { method: "DELETE" }),

  stopChat: (taskId: string) => http(`/rag/v3/stop?taskId=${encodeURIComponent(taskId)}`, { method: "POST" }),
};

export const CHAT_URL = (question: string, conversationId?: string) => {
  const q = new URLSearchParams({ question });
  if (conversationId) q.set("conversationId", conversationId);
  return `${BASE}/rag/v3/chat?${q.toString()}`;
};
