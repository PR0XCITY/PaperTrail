import { useState, useEffect } from "react";
import FileUploader from "./components/FileUploader";
import ChatWindow from "./components/ChatWindow";
import { startKeepAlive } from "./utils/keepAlive";

export default function App() {
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [hasUpload, setHasUpload] = useState(false);

  useEffect(() => {
    startKeepAlive();
  }, []);

  function handleUploadSuccess(info, filename) {
    setHasUpload(true);
    setUploadedFiles((prev) => [
      { name: filename, pages: info.pages, chunks: info.chunks },
      ...prev,
    ]);
  }

  return (
    <div className="app-layout">
      {/* ── Sidebar ────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <span className="logo-icon">📄</span>
          <span className="logo-text">PaperTrail</span>
        </div>
        <p className="tagline">Upload a PDF. Ask anything.</p>

        <FileUploader onUploadSuccess={handleUploadSuccess} />

        {uploadedFiles.length > 0 && (
          <div className="file-list">
            <h3 className="file-list-title">Indexed Documents</h3>
            {uploadedFiles.map((f, i) => (
              <div key={i} className="file-item">
                <span className="file-icon">📑</span>
                <div className="file-meta">
                  <span className="file-name" title={f.name}>{f.name}</span>
                  <span className="file-stats">{f.pages}p · {f.chunks} chunks</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </aside>

      {/* ── Main Chat Area ─────────────────────────────────────── */}
      <main className="chat-area">
        <header className="chat-area-header">
          <h1 className="chat-area-title">Chat</h1>
          <span className="chat-area-subtitle">
            {hasUpload ? `${uploadedFiles.length} document${uploadedFiles.length !== 1 ? "s" : ""} indexed` : "No documents yet"}
          </span>
        </header>

        {hasUpload ? (
          <ChatWindow />
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon">📂</div>
            <h2 className="empty-state-title">No documents indexed</h2>
            <p className="empty-state-body">
              Upload a PDF in the sidebar to start asking questions.
            </p>
          </div>
        )}
      </main>
    </div>
  );
}
