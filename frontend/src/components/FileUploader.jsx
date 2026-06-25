import { useState, useRef } from "react";
import { uploadPDF } from "../api/client";

export default function FileUploader({ onUploadSuccess }) {
  const [status, setStatus] = useState("idle"); // idle | uploading | done | error
  const [progress, setProgress] = useState(0);
  const [info, setInfo] = useState(null);
  const [error, setError] = useState("");
  const fileRef = useRef(null);

  async function handleFileChange(e) {
    const file = e.target.files[0];
    if (!file) return;

    const filename = file.name;
    setStatus("uploading");
    setProgress(0);
    setError("");
    setInfo(null);

    try {
      const result = await uploadPDF(file, (pct) => setProgress(pct));
      setInfo(result);
      setStatus("done");
      // Pass result AND filename so parent can track indexed files
      onUploadSuccess(result, filename);
      // Reset input so same file can be re-uploaded
      if (fileRef.current) fileRef.current.value = "";
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  return (
    <div className="uploader">
      <h2 className="uploader-title">Upload PDF</h2>

      <label className="upload-btn" htmlFor="pdf-input">
        {status === "uploading" ? `Uploading… ${progress}%` : "⬆ Choose PDF"}
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

      {status === "done" && info && (
        <p className="upload-success">
          ✓ {info.pages} page{info.pages !== 1 ? "s" : ""}, {info.chunks} chunks indexed
        </p>
      )}

      {status === "error" && (
        <p className="upload-error">✗ {error}</p>
      )}
    </div>
  );
}
