import { useEffect, useRef, useState } from "react";
import { useStreamChat } from "../hooks/useStreamChat";

export default function ChatPage() {
  const { messages, streaming, send, stop, reset } = useStreamChat();
  const [text, setText] = useState("");
  const bodyRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    const q = text.trim();
    if (!q) return;
    setText("");
    void send(q);
  };

  return (
    <div className="chat">
      <div className="chat-head">
        <strong>智能问答</strong>
        <button className="ghost" onClick={reset} disabled={streaming}>新会话</button>
      </div>
      <div className="chat-body" ref={bodyRef}>
        {messages.length === 0 && <div className="empty">输入问题开始对话（基于知识库的 RAG 流式问答）</div>}
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <div className="who">{m.role === "user" ? "我" : "助手"}</div>
            {m.think && <div className="think">{m.think}</div>}
            <div className="bubble">{m.content || (streaming && i === messages.length - 1 ? "…" : "")}</div>
            {m.role === "assistant" && (m.intents?.length || m.chunks != null) && (
              <div className="meta">
                {m.chunks != null && <span className="tag">检索 {m.chunks} 段</span>}
                {m.intents?.map((it) => (
                  <span className="tag" key={it.code}>意图 {it.name} {it.score.toFixed(2)}</span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <div className="row">
          <input
            type="text"
            placeholder="输入问题，回车发送"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") submit(); }}
            disabled={streaming}
          />
          {streaming ? (
            <button className="ghost" onClick={() => void stop()}>停止</button>
          ) : (
            <button onClick={submit}>发送</button>
          )}
        </div>
      </div>
    </div>
  );
}
