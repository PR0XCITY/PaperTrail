import { useState, useRef } from "react";
import { uploadPDF } from "../api/client";

/**
 * PDF upload button with progress bar and status feedback.
 * On success, calls onUploadSuccess({document_id, name, pages, chunks}).
 */
export default function FileUploader({ onUploadSuccess }) {
  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  async function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;

    setStatus("uploading");
    setProgress(0);
    setError("");

    try {
      const result = await uploadPDF(file, (pct) => setProgress(pct));
      setStatus("done");
      onUploadSuccess(result);
      if (fileRef.current) fileRef.current.value = "";
      // Auto-reset after 3 s so user can upload another
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  return (
    <div className="uploader">
      <h2 className="uploader-title">Upload PDF</h2>

      <label
        className={`upload-btn ${status === "uploading" ? "upload-btn--busy" : ""}`}
        htmlFor="pdf-input"
      >
        {status === "uploading" ? `Indexing… ${progress}%` : "⬆ Choose PDF"}
      </label>

      <input
        id="pdf-input"
        type="file"
        accept=".pdf"
        ref={fileRef}
        onChange={handleFileChange}
        disabled={status === "uploading"}
        style={{ display: "none" }}
      />

      {status === "uploading" && (
        <div className="progress-bar-track">
          <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
        </div>
      )}

      {status === "done" && (
        <p className="upload-success">✓ Document indexed</p>
      )}

      {status === "error" && (
        <p className="upload-error">✗ {error}</p>
      )}
    </div>
  );
}
