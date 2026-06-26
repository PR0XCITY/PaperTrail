/**
 * PaperTrail API client
 *
 * All API calls go through this module. BASE URL is read from VITE_API_URL
 * so the same build works locally and on Vercel without code changes.
 */

const BASE = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "http://localhost:8000" : "");

// ── Upload ────────────────────────────────────────────────────────────────────

/**
 * Upload a PDF to the backend.
 * @param {File} file
 * @param {(pct: number) => void} onProgress  0–100
 * @returns {Promise<{document_id, name, pages, chunks}>}
 */
export function uploadPDF(file, onProgress) {
  const form = new FormData();
  form.append("file", file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        const detail = (() => {
          try { return JSON.parse(xhr.responseText).detail; }
          catch { return xhr.statusText || "Upload failed"; }
        })();
        reject(new Error(detail));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error during upload")));
    xhr.open("POST", `${BASE}/upload`);
    xhr.send(form);
  });
}

// ── Documents ─────────────────────────────────────────────────────────────────

/**
 * Fetch the list of all indexed documents.
 * @returns {Promise<{documents: Array<{document_id, name, pages, chunks, created_at}>}>}
 */
export async function listDocuments() {
  const res = await fetch(`${BASE}/documents`);
  if (!res.ok) throw new Error("Failed to fetch document list");
  return res.json();
}

/**
 * Delete a document from all indexes.
 * @param {string} documentId
 */
export async function deleteDocument(documentId) {
  const res = await fetch(`${BASE}/documents/${documentId}`, { method: "DELETE" });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(detail.detail || "Delete failed");
  }
  return res.json();
}

// ── Streaming Query ───────────────────────────────────────────────────────────

/**
 * Send a query via POST and stream the SSE response using fetch + ReadableStream.
 * (Native EventSource only supports GET, so we use fetch for POST bodies.)
 *
 * SSE events from the server:
 *   sources   — [{document_id, source, page, section}]
 *   token     — one token of the LLM response
 *   followups — ["q1?", "q2?", "q3?"]
 *   done      — signals end of stream
 *
 * @returns {AbortController} — call .abort() to cancel mid-stream
 */
export function streamQuery({
  question,
  documentId,
  sessionId,
  searchAll = false,
  onSources,
  onToken,
  onFollowups,
  onDone,
  onError,
}) {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question,
          document_id: documentId ?? null,
          session_id: sessionId,
          search_all: searchAll,
        }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(body.detail || `Server error ${res.status}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop(); // keep last incomplete line for next iteration

        let currentEvent = null;
        for (const line of lines) {
          if (line.startsWith("event:")) {
            currentEvent = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            // SSE spec: lines are "data: <value>" — slice(6) skips the mandatory
            // "data: " prefix (including the space). Do NOT .trim() here:
            // LLM tokenizers emit space-prefixed tokens like " word", and
            // trimming them destroys the spaces between words.
            const data = line.startsWith("data: ") ? line.slice(6) : line.slice(5);
            switch (currentEvent) {
              case "sources":
                try { onSources?.(JSON.parse(data)); } catch {}
                break;
              case "token":
                onToken?.(data.replace(/\\n/g, "\n"));
                break;
              case "followups":
                try { onFollowups?.(JSON.parse(data)); } catch {}
                break;
              case "done":
                onDone?.();
                break;
            }
            currentEvent = null;
          }
        }
      }
    } catch (err) {
      if (err.name !== "AbortError") {
        onError?.(err);
      }
    }
  })();

  return controller;
}
