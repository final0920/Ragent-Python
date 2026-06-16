// 后端 REST 封装。base 由 Vite 代理到 9090。
const BASE = "/api/ragent";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(BASE + path, init);
  if (!resp.ok) throw new Error(`${resp.status} ${await resp.text()}`);
  return (await resp.json()) as T;
}

export interface KnowledgeBase {
  id: string;
  name: string;
  collection_name: string;
}

export interface IntentNode {
  id: string;
  intent_code: string;
  name: string;
  level: number;
  kind: number;
  collection_name: string;
  enabled: boolean;
}

export const api = {
  health: () => http<{ status: string; db: boolean }>("/health"),

  listKnowledgeBases: () => http<KnowledgeBase[]>("/knowledge-base"),
  createKnowledgeBase: (name: string) =>
    http<{ id: string; name: string; collection_name: string }>("/knowledge-base", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    }),
  uploadDoc: (kbId: string, file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return http<{ doc_id: string; chunk_count: number }>(
      `/knowledge-base/${kbId}/docs/upload`,
      { method: "POST", body: fd }
    );
  },

  listIntents: () => http<IntentNode[]>("/intent-tree"),
  createIntent: (body: Record<string, unknown>) =>
    http<{ id: string; intent_code: string }>("/intent-tree", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),

  stopChat: (taskId: string) =>
    http<{ stopped: boolean }>(`/rag/v3/stop?taskId=${encodeURIComponent(taskId)}`, {
      method: "POST",
    }),
};

export const CHAT_URL = (question: string, conversationId?: string) => {
  const q = new URLSearchParams({ question });
  if (conversationId) q.set("conversationId", conversationId);
  return `${BASE}/rag/v3/chat?${q.toString()}`;
};
