import { useState, useRef } from "react";
import { uploadPDF } from "../api/client";

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
      setTimeout(() => setStatus("idle"), 3000);
    } catch (err) {
      setError(err.message);
      setStatus("error");
    }
  }

  return (
    <div className="flex flex-col gap-2 mt-4 w-full">
      <label
        className={`w-full py-2 px-4 rounded-lg flex justify-center items-center gap-2 text-body-sm font-body-sm font-medium transition-colors cursor-pointer
          ${status === "uploading" 
            ? "bg-surface-container-high text-on-surface-variant cursor-not-allowed" 
            : "bg-secondary-container text-on-secondary-container hover:bg-secondary"
          }
        `}
        htmlFor="pdf-input"
      >
        <span className="material-symbols-outlined text-sm">
          {status === "uploading" ? "hourglass_empty" : "add"}
        </span> 
        {status === "uploading" ? `Indexing… ${progress}%` : "New Analysis"}
      </label>

      <input
        id="pdf-input"
        type="file"
        accept=".pdf"
        ref={fileRef}
        onChange={handleFileChange}
        disabled={status === "uploading"}
        className="hidden"
      />

      {status === "uploading" && (
        <div className="h-1 w-full bg-outline-variant/30 rounded-full overflow-hidden">
          <div className="h-full bg-secondary transition-all" style={{ width: `${progress}%` }} />
        </div>
      )}

      {status === "done" && (
        <p className="text-secondary text-label-mono font-label-mono flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">check_circle</span> Document indexed
        </p>
      )}

      {status === "error" && (
        <p className="text-error text-label-mono font-label-mono flex items-center gap-1">
          <span className="material-symbols-outlined text-[14px]">error</span> {error}
        </p>
      )}
    </div>
  );
}
