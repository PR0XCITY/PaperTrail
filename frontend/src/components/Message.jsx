import ReactMarkdown from "react-markdown";

/**
 * Renders a single chat message bubble.
 *
 * Props:
 *   role      — "user" | "assistant"
 *   content   — string (markdown supported for assistant)
 *   sources   — Array<{source: string, page: number}> (assistant only)
 *   streaming — bool  (shows blinking cursor when true)
 */
export default function Message({ role, content, sources = [], streaming = false }) {
  const isAssistant = role === "assistant";

  return (
    <div className={`message message-${role}`}>
      <span className="message-role">{role === "user" ? "You" : "PaperTrail"}</span>

      <div className="message-content">
        {isAssistant ? (
          <>
            <ReactMarkdown>{content || "\u00a0"}</ReactMarkdown>
            {streaming && <span className="cursor" aria-hidden="true" />}
          </>
        ) : (
          <p>{content}</p>
        )}
      </div>

      {/* Citation chips — only for assistant, only when sources exist */}
      {isAssistant && sources.length > 0 && (
        <div className="citations" aria-label="Source citations">
          {sources.map((s, i) => (
            <span key={i} className="citation-chip" title={s.source}>
              📄 {s.source} · p.{s.page}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
