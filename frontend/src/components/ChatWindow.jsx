import { useState, useRef, useEffect } from "react";
import { streamQuery, uploadPDF } from "../api/client";
import Message from "./Message";

export default function ChatWindow({
  activeDocumentId,
  sessionId,
  searchAll,
  messages,
  onMessagesChange,
  onUploadSuccess,
}) {
  const [inputText, setInputText] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [uploading, setUploading] = useState(false);
  const controllerRef = useRef(null);
  const bottomRef     = useRef(null);
  const fileInputRef  = useRef(null);

  async function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    try {
      const result = await uploadPDF(file, () => {});
      if (onUploadSuccess) onUploadSuccess(result);
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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

  function sendMessage(text) {
    const q = (text ?? inputText).trim();
    if (!q || streaming) return;

    controllerRef.current?.abort();

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

  return (
    <>
      {/* Chat History */}
      <div className="flex-1 overflow-y-auto p-margin_md pb-32 flex flex-col items-center">
        <div className="w-full max-w-main_max_width flex flex-col gap-8">
          {messages.length === 0 && (
            <div className="text-center text-on-surface-variant mt-20">
              <span className="material-symbols-outlined text-4xl mb-4 opacity-50">forum</span>
              <p className="text-body-base font-body-base">
                {canSend
                  ? "Ask anything about the selected document."
                  : "Upload a document to begin."}
              </p>
            </div>
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
      </div>

      {/* Chat Input Area */}
      <div className="absolute bottom-0 left-0 right-0 p-margin_md bg-gradient-to-t from-background via-background to-transparent flex justify-center">
        <div className="w-full max-w-main_max_width relative">
          
          <div className="bg-surface-container border border-outline-variant rounded-lg p-2 flex items-end shadow-lg focus-within:border-secondary focus-within:ring-1 focus-within:ring-secondary/50 transition-all">
            <button 
              className="w-10 h-10 flex items-center justify-center text-outline hover:text-secondary transition-colors rounded-lg flex-shrink-0" 
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <span className="material-symbols-outlined">{uploading ? "hourglass_empty" : "attach_file"}</span>
            </button>
            <input 
              type="file" 
              accept=".pdf" 
              ref={fileInputRef} 
              onChange={handleFileChange} 
              className="hidden" 
            />
            <textarea
              className="w-full bg-transparent border-none text-on-surface text-body-base font-body-base placeholder:text-outline-variant resize-none focus:ring-0 focus:outline-none max-h-32 py-2 px-2"
              placeholder={canSend ? "Ask a follow-up question..." : "Upload a PDF first…"}
              rows={1}
              style={{ minHeight: "44px" }}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={streaming || !canSend}
            />
            <button
              className="w-10 h-10 flex items-center justify-center bg-secondary text-on-secondary hover:bg-secondary-container transition-colors rounded-lg flex-shrink-0 ml-2 disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={() => sendMessage()}
              disabled={streaming || !inputText.trim() || !canSend}
            >
              <span className="material-symbols-outlined">{streaming ? "hourglass_empty" : "send"}</span>
            </button>
          </div>
          <div className="text-center mt-2">
            <span className="text-label-mono font-label-mono text-outline-variant text-[10px]">PaperTrail AI uses Llama 3.3. Verify important claims.</span>
          </div>
        </div>
      </div>
    </>
  );
}
