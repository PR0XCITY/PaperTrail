import ReactMarkdown from "react-markdown";

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

  if (!isAssistant) {
    return (
      <div className="flex justify-end w-full">
        <div className="bg-surface-container-high text-on-surface px-5 py-3 rounded-lg rounded-tr-sm max-w-[85%] border border-outline-variant/20 shadow-sm">
          <p className="text-body-base font-body-base whitespace-pre-wrap">{content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex justify-start w-full gap-4">
      <div className="w-8 h-8 rounded-lg bg-surface-container-high flex-shrink-0 flex items-center justify-center border border-outline-variant">
        <span className="material-symbols-outlined text-secondary text-sm">smart_toy</span>
      </div>
      
      <div className="flex flex-col gap-3 max-w-[90%]">
        <div className="bg-surface-container text-on-surface px-5 py-4 rounded-lg rounded-tl-sm border border-outline-variant shadow-sm markdown-content text-body-base font-body-base text-on-surface-variant leading-relaxed">
          <ReactMarkdown>{content || "\u00a0"}</ReactMarkdown>
          {streaming && <span className="inline-block w-2 h-4 bg-secondary ml-1 align-middle cursor-blink"></span>}
        </div>

        {/* Citations */}
        {sources.length > 0 && (
          <div className="flex flex-col gap-2 mt-1">
            <span className="text-label-upper font-label-upper text-outline tracking-wider">Source Citations</span>
            <div className="flex flex-wrap gap-2">
              {sources.map((s, i) => (
                <button
                  key={i}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-secondary-container/10 border-l-2 border-secondary-container text-secondary-container text-label-mono font-label-mono cursor-pointer hover:bg-secondary-container/20 transition-colors"
                  onClick={() => handleCitationClick(s)}
                  title={`${s.source}` + (s.section ? `\n${s.section}` : "") + `\nClick to copy reference`}
                >
                  <span className="material-symbols-outlined text-[14px]">description</span>
                  <span>{s.source} · Page {s.page}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Follow-ups */}
        {!streaming && followups.length > 0 && (
          <div className="flex flex-col gap-2 mt-2">
            <span className="text-label-upper font-label-upper text-outline tracking-wider">Suggested Questions</span>
            <div className="flex flex-wrap gap-2">
              {followups.map((q, i) => (
                <button
                  key={i}
                  className="px-3 py-1.5 bg-surface-container-highest border border-outline-variant text-on-surface-variant hover:bg-surface hover:text-on-surface hover:border-secondary transition-colors rounded-lg text-body-sm font-body-sm text-left"
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
    </div>
  );
}
