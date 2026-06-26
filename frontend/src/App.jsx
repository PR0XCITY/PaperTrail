import { useState, useEffect, useRef } from "react";
import FileUploader from "./components/FileUploader";
import ChatWindow from "./components/ChatWindow";
import DocumentList from "./components/DocumentList";
import { startKeepAlive } from "./utils/keepAlive";
import { listDocuments } from "./api/client";

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [activeDocumentId, setActiveDocumentId] = useState(null);
  const [searchAll, setSearchAll] = useState(false);

  // Messages stored per session key so history persists when switching docs
  const [messagesMap, setMessagesMap] = useState({});

  // Per-document session IDs (one per document + one for "search all")
  const sessionIdsRef = useRef(new Map());
  function getSessionId(key) {
    if (!sessionIdsRef.current.has(key)) {
      sessionIdsRef.current.set(key, crypto.randomUUID());
    }
    return sessionIdsRef.current.get(key);
  }

  useEffect(() => {
    startKeepAlive();
    listDocuments()
      .then(({ documents: docs }) => {
        if (docs.length > 0) {
          setDocuments(docs);
          setActiveDocumentId(docs[0].document_id);
        }
      })
      .catch(() => {});
  }, []);

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleUploadSuccess(result) {
    const newDoc = {
      document_id: result.document_id,
      name:        result.name,
      pages:       result.pages,
      chunks:      result.chunks,
    };
    setDocuments((prev) => [newDoc, ...prev]);
    setActiveDocumentId(result.document_id);
    setSearchAll(false);
  }

  function handleSelectDocument(docId) {
    setActiveDocumentId(docId);
    setSearchAll(false);
  }

  function handleDeleteDocument(docId) {
    setDocuments((prev) => prev.filter((d) => d.document_id !== docId));
    if (activeDocumentId === docId) {
      const remaining = documents.filter((d) => d.document_id !== docId);
      setActiveDocumentId(remaining.length > 0 ? remaining[0].document_id : null);
    }
    // Clean up stored messages for deleted doc
    setMessagesMap((prev) => {
      const next = { ...prev };
      delete next[docId];
      return next;
    });
  }

  // Messages helpers — per session key
  function getMessages(key) {
    return messagesMap[key] ?? [];
  }
  function setMessages(key, updater) {
    setMessagesMap((prev) => ({
      ...prev,
      [key]: typeof updater === "function" ? updater(prev[key] ?? []) : updater,
    }));
  }

  // ── Derived ───────────────────────────────────────────────────────────────

  const activeDoc  = documents.find((d) => d.document_id === activeDocumentId);
  const sessionKey = searchAll ? "__all__" : (activeDocumentId ?? "__none__");
  const sessionId  = getSessionId(sessionKey);
  const canChat    = searchAll || !!activeDocumentId;

  return (
    <div className="app-layout">
      {/* ── Sidebar ──────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="logo-icon">📄</span>
          <span className="logo-text">PaperTrail</span>
        </div>
        <p className="tagline">Upload a PDF. Ask anything.</p>

        <FileUploader onUploadSuccess={handleUploadSuccess} />

        {documents.length > 0 && (
          <DocumentList
            documents={documents}
            activeDocumentId={activeDocumentId}
            onSelect={handleSelectDocument}
            onDelete={handleDeleteDocument}
            searchAll={searchAll}
            onSearchAllChange={setSearchAll}
          />
        )}
      </aside>

      {/* ── Main Chat ─────────────────────────────────────────── */}
      <main className="chat-area">
        <header className="chat-area-header">
          <h1 className="chat-area-title">Chat</h1>
          <div className="chat-context">
            {searchAll ? (
              <span className="context-badge context-badge--all">
                🔍 Searching all {documents.length} document{documents.length !== 1 ? "s" : ""}
              </span>
            ) : activeDoc ? (
              <span className="context-badge context-badge--doc">
                <span className="context-pulse" />
                {activeDoc.name}
              </span>
            ) : (
              <span className="context-badge context-badge--none">No document selected</span>
            )}
          </div>
        </header>

        {canChat ? (
          <ChatWindow
            activeDocumentId={searchAll ? null : activeDocumentId}
            sessionId={sessionId}
            searchAll={searchAll}
            messages={getMessages(sessionKey)}
            onMessagesChange={(updater) => setMessages(sessionKey, updater)}
          />
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📂</div>
            <h2 className="empty-state-title">No document selected</h2>
            <p className="empty-state-body">
              Upload a PDF in the sidebar to start asking questions about it.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
