// 用 fetch + ReadableStream 消费后端 SSE（事件帧：event:/data:）。
import { useCallback, useRef, useState } from "react";
import { CHAT_URL, api, getToken } from "../api";

export interface ChatMsg {
  role: "user" | "assistant";
  content: string;
  think?: string;
  intents?: { code: string; name: string; score: number }[];
  chunks?: number;
}

interface SseEvent {
  event: string;
  data: any;
}

function parseFrames(buffer: string): { events: SseEvent[]; rest: string } {
  const parts = buffer.split("\n\n");
  const rest = parts.pop() ?? "";
  const events: SseEvent[] = [];
  for (const block of parts) {
    let ev = "message";
    let data = "";
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) ev = line.slice(6).trim();
      else if (line.startsWith("data:")) data += line.slice(5).trim();
    }
    if (!data) continue;
    try {
      events.push({ event: ev, data: JSON.parse(data) });
    } catch {
      /* 忽略心跳/非 JSON */
    }
  }
  return { events, rest };
}

export function useStreamChat() {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [streaming, setStreaming] = useState(false);
  const convId = useRef<string | undefined>(undefined);
  const taskId = useRef<string | undefined>(undefined);
  const abort = useRef<AbortController | null>(null);

  const send = useCallback(async (question: string) => {
    if (!question.trim() || streaming) return;
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);
    setStreaming(true);
    const ctrl = new AbortController();
    abort.current = ctrl;

    try {
      const headers: Record<string, string> = { Accept: "text/event-stream" };
      const tok = getToken();
      if (tok) headers.Authorization = `Bearer ${tok}`;
      const resp = await fetch(CHAT_URL(question, convId.current), {
        signal: ctrl.signal,
        headers,
      });
      const reader = resp.body!.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const { events, rest } = parseFrames(buf);
        buf = rest;
        for (const e of events) {
          if (e.event === "meta") {
            if (e.data.conversationId) convId.current = e.data.conversationId;
            if (e.data.taskId) taskId.current = e.data.taskId;
            if (e.data.intents || e.data.chunks != null)
              setMessages((m) => patchLast(m, (a) => ({ ...a, intents: e.data.intents ?? a.intents, chunks: e.data.chunks ?? a.chunks })));
          } else if (e.event === "message") {
            if (e.data.type === "response")
              setMessages((m) => patchLast(m, (a) => ({ ...a, content: a.content + e.data.content })));
            else if (e.data.type === "think")
              setMessages((m) => patchLast(m, (a) => ({ ...a, think: (a.think ?? "") + e.data.content })));
          } else if (e.event === "cancel") {
            setMessages((m) => patchLast(m, (a) => ({ ...a, content: a.content + "\n\n[已停止]" })));
          } else if (e.event === "error") {
            setMessages((m) => patchLast(m, (a) => ({ ...a, content: a.content + `\n\n[错误] ${e.data.message}` })));
          }
        }
      }
    } catch (err: any) {
      if (err?.name !== "AbortError")
        setMessages((m) => patchLast(m, (a) => ({ ...a, content: a.content + `\n\n[连接错误] ${err}` })));
    } finally {
      setStreaming(false);
      abort.current = null;
    }
  }, [streaming]);

  const stop = useCallback(async () => {
    if (taskId.current) {
      try { await api.stopChat(taskId.current); } catch { /* ignore */ }
    }
    abort.current?.abort();
    setStreaming(false);
  }, []);

  const reset = useCallback(() => {
    convId.current = undefined;
    setMessages([]);
  }, []);

  return { messages, streaming, send, stop, reset };
}

function patchLast(list: ChatMsg[], fn: (a: ChatMsg) => ChatMsg): ChatMsg[] {
  if (!list.length) return list;
  const copy = list.slice();
  copy[copy.length - 1] = fn(copy[copy.length - 1]);
  return copy;
}
