import { useState, useEffect, useRef } from "react";
import FileUploader from "./components/FileUploader";
import ChatWindow from "./components/ChatWindow";
import DocumentList from "./components/DocumentList";
import { startKeepAlive } from "./utils/keepAlive";
import { deleteDocumentKeepAlive } from "./api/client";

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
  }, []);

  // Cleanup session documents on unload
  useEffect(() => {
    const handleUnload = () => {
      documents.forEach(doc => {
        deleteDocumentKeepAlive(doc.document_id);
      });
    };
    window.addEventListener("beforeunload", handleUnload);
    window.addEventListener("pagehide", handleUnload);
    return () => {
      window.removeEventListener("beforeunload", handleUnload);
      window.removeEventListener("pagehide", handleUnload);
    };
  }, [documents]);

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
    setMessagesMap((prev) => {
      const next = { ...prev };
      delete next[docId];
      return next;
    });
  }

  function getMessages(key) {
    return messagesMap[key] ?? [];
  }
  function setMessages(key, updater) {
    setMessagesMap((prev) => ({
      ...prev,
      [key]: typeof updater === "function" ? updater(prev[key] ?? []) : updater,
    }));
  }

  const activeDoc  = documents.find((d) => d.document_id === activeDocumentId);
  const sessionKey = searchAll ? "__all__" : (activeDocumentId ?? "__none__");
  const sessionId  = getSessionId(sessionKey);
  const canChat    = searchAll || !!activeDocumentId;

  return (
    <div className="bg-background text-on-surface font-body-base antialiased h-screen overflow-hidden flex flex-col">
      {/* TopAppBar */}
      <header className="fixed top-0 w-full h-[52px] z-50 border-b border-outline-variant bg-surface/90 backdrop-blur-md flex justify-between items-center px-margin_md text-on-surface font-headline-md text-headline-md">
        <div className="flex items-center gap-2 text-on-surface font-bold">
          <span className="material-symbols-outlined text-secondary" style={{ fontVariationSettings: "'FILL' 1" }}>menu_book</span>
          PaperTrail
        </div>
        <div className="flex items-center gap-4 text-body-sm font-body-sm text-on-surface-variant">
          <span>Model: Llama 3.3 · Groq</span>
          <button className="flex items-center hover:bg-surface-container-high transition-colors p-1 rounded-lg text-secondary">
            <span className="material-symbols-outlined text-xl">account_circle</span>
          </button>
        </div>
      </header>

      <div className="flex flex-1 pt-[52px] overflow-hidden">
        {/* SideNavBar */}
        <nav className="hidden md:flex flex-col fixed left-0 top-[52px] h-[calc(100vh-52px)] w-[280px] border-r border-outline-variant bg-surface-container-low py-margin_sm z-40">
          <div className="px-margin_md mb-6">
            <h2 className="text-headline-md font-headline-md text-on-surface mb-1">Research Hub</h2>
            <p className="text-body-sm font-body-sm text-on-surface-variant">Precision Synthesis</p>
            <FileUploader onUploadSuccess={handleUploadSuccess} />
          </div>

          <div className="flex-1 overflow-y-auto flex flex-col gap-1">
            <DocumentList
              documents={documents}
              activeDocumentId={activeDocumentId}
              onSelect={handleSelectDocument}
              onDelete={handleDeleteDocument}
              searchAll={searchAll}
              onSearchAllChange={setSearchAll}
            />
          </div>
        </nav>

        {/* Main Content Area */}
        <main className="flex-1 flex flex-col ml-0 md:ml-[280px] relative w-full h-full bg-background">
          <ChatWindow
            activeDocumentId={searchAll ? null : activeDocumentId}
            sessionId={sessionId}
            searchAll={searchAll}
            messages={getMessages(sessionKey)}
            onMessagesChange={(updater) => setMessages(sessionKey, updater)}
            onUploadSuccess={handleUploadSuccess}
          />
        </main>
      </div>
    </div>
  );
}
