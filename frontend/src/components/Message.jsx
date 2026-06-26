import ReactMarkdown from "react-markdown";

/**
 * Single chat message bubble.
 *
 * Props:
 *   role            — "user" | "assistant"
 *   content         — string (markdown for assistant)
 *   sources         — [{document_id, source, page, section}]
 *   followups       — string[] suggested follow-up questions
 *   streaming       — bool (shows blinking cursor)
 *   onFollowupSelect — (question: string) => void
 */
export default function Message({
  role,
  content,
  sources = [],
  followups = [],
  streaming = false,
  onFollowupSelect,
}) {
  const isAssistant = role === "assistant";

  function handleCitationClick(s) {
    const ref = `${s.source} — Page ${s.page}${s.section ? ` (${s.section})` : ""}`;
    navigator.clipboard?.writeText(ref).catch(() => {});
  }

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

      {/* Citation chips */}
      {isAssistant && sources.length > 0 && (
        <div className="citations" aria-label="Source citations">
          {sources.map((s, i) => (
            <button
              key={i}
              className="citation-chip"
              onClick={() => handleCitationClick(s)}
              title={
                `${s.source}` +
                (s.section ? `\n${s.section}` : "") +
                `\nClick to copy reference`
              }
              aria-label={`Source: ${s.source}, page ${s.page}`}
            >
              <span className="citation-icon">📄</span>
              <span className="citation-page">p.{s.page}</span>
              {s.section && (
                <span className="citation-section">{s.section}</span>
              )}
            </button>
          ))}
        </div>
      )}

      {/* Follow-up chips — only after streaming completes */}
      {isAssistant && !streaming && followups.length > 0 && (
        <div className="followups">
          <span className="followups-label">Suggested questions</span>
          <div className="followup-chips">
            {followups.map((q, i) => (
              <button
                key={i}
                className="followup-chip"
                onClick={() => onFollowupSelect?.(q)}
                title={q}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
