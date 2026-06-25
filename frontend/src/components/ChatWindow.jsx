import { useState, useRef, useEffect } from "react";
import { streamQuery } from "../api/client";
import Message from "./Message";

export default function ChatWindow() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const esRef = useRef(null);
  const bottomRef = useRef(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /** Append a token to the last assistant message */
  function appendToken(token) {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === "assistant") {
        return [...prev.slice(0, -1), { ...last, content: last.content + token }];
      }
      return [...prev, { role: "assistant", content: token, sources: [] }];
    });
  }

  /** Attach sources to the last assistant message */
  function attachSources(sources) {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === "assistant") {
        return [...prev.slice(0, -1), { ...last, sources }];
      }
      return prev;
    });
  }

  function sendMessage() {
    const q = input.trim();
    if (!q || streaming) return;

    // Close any existing stream
    esRef.current?.close();

    // Add user message
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setInput("");
    setStreaming(true);

    // Seed an empty assistant bubble
    setMessages((prev) => [...prev, { role: "assistant", content: "", sources: [] }]);

    esRef.current = streamQuery(
      q,
      (sources) => attachSources(sources),   // onSources
      (token) => appendToken(token),          // onToken
      () => setStreaming(false),              // onDone
      (err) => {                             // onError
        appendToken(`\n\n*Error: ${err.message}*`);
        setStreaming(false);
      }
    );
  }

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }

  return (
    <div className="chat-window">
      <div className="messages">
        {messages.length === 0 && (
          <p className="empty-hint">Ask anything about your uploaded PDF.</p>
        )}

        {messages.map((msg, i) => (
          <Message
            key={i}
            role={msg.role}
            content={msg.content}
            sources={msg.sources || []}
            streaming={streaming && i === messages.length - 1 && msg.role === "assistant"}
          />
        ))}

        <div ref={bottomRef} />
      </div>

      <div className="input-row">
        <textarea
          className="chat-input"
          id="chat-input"
          placeholder="Ask a question about your PDF…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={streaming}
          rows={2}
        />
        <button
          id="send-btn"
          className="send-btn"
          onClick={sendMessage}
          disabled={streaming || !input.trim()}
        >
          {streaming ? "…" : "Send"}
        </button>
      </div>
    </div>
  );
}
