import { useState, useRef, useEffect } from "react";
import { streamQuery } from "../api/client";
import Message from "./Message";

/**
 * Chat window — messages are owned by App.jsx (via props) so history
 * persists when the user switches between documents.
 *
 * Props:
 *   activeDocumentId  — selected document UUID (null = search all)
 *   sessionId         — conversation UUID for this document/context
 *   searchAll         — bool: ignore document_id filter
 *   messages          — Message[] owned by App.jsx
 *   onMessagesChange  — (updater: fn | array) => void
 */
export default function ChatWindow({
  activeDocumentId,
  sessionId,
  searchAll,
  messages,
  onMessagesChange,
}) {
  const [inputText, setInputText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const controllerRef = useRef(null);
  const bottomRef     = useRef(null);

  // Auto-scroll whenever messages update
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ── Mutators (operate on parent-owned messages array) ─────────────────────

  function appendToken(token) {
    onMessagesChange((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === "assistant") {
        return [...prev.slice(0, -1), { ...last, content: last.content + token }];
      }
      return [...prev, { role: "assistant", content: token, sources: [], followups: [] }];
    });
  }

  function attachSources(sources) {
    onMessagesChange((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === "assistant") {
        return [...prev.slice(0, -1), { ...last, sources }];
      }
      return prev;
    });
  }

  function attachFollowups(followups) {
    onMessagesChange((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === "assistant") {
        return [...prev.slice(0, -1), { ...last, followups }];
      }
      return prev;
    });
  }

  // ── Send ──────────────────────────────────────────────────────────────────

  function sendMessage(text) {
    const q = (text ?? inputText).trim();
    if (!q || streaming) return;

    // Cancel any in-flight stream
    controllerRef.current?.abort();

    // Optimistic UI: append user + empty assistant bubble
    onMessagesChange((prev) => [
      ...prev,
      { role: "user",      content: q,  sources: [], followups: [] },
      { role: "assistant", content: "", sources: [], followups: [] },
    ]);
    setInputText("");
    setStreaming(true);

    controllerRef.current = streamQuery({
      question:    q,
      documentId:  activeDocumentId,
      sessionId,
      searchAll,
      onSources:   attachSources,
      onToken:     appendToken,
      onFollowups: attachFollowups,
      onDone:      () => setStreaming(false),
      onError:     (err) => {
        appendToken(`\n\n*Error: ${err.message}*`);
        setStreaming(false);
      },
    });
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  const canSend = !!activeDocumentId || searchAll;

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.length === 0 && (
          <p className="empty-hint">
            {canSend
              ? "Ask anything about the selected document."
              : "Select a document from the sidebar to begin."}
          </p>
        )}

        {messages.map((msg, i) => (
          <Message
            key={i}
            role={msg.role}
            content={msg.content}
            sources={msg.sources || []}
            followups={msg.followups || []}
            streaming={streaming && i === messages.length - 1 && msg.role === "assistant"}
            onFollowupSelect={(q) => sendMessage(q)}
          />
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="input-row">
        <textarea
          className="chat-input"
          id="chat-input"
          placeholder={canSend ? "Ask a question about your PDF…" : "Select a PDF first…"}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={streaming || !canSend}
          rows={2}
        />
        <button
          id="send-btn"
          className="send-btn"
          onClick={() => sendMessage()}
          disabled={streaming || !inputText.trim() || !canSend}
        >
          {streaming ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
