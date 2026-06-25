const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

/**
 * Upload a PDF file to the backend.
 * @param {File} file
 * @param {(pct: number) => void} onProgress  0–100
 * @returns {Promise<{message: string, pages: number, chunks: number}>}
 */
export async function uploadPDF(file, onProgress) {
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
        const err = (() => {
          try { return JSON.parse(xhr.responseText).detail; }
          catch { return xhr.statusText; }
        })();
        reject(new Error(err));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.open("POST", `${BASE}/upload`);
    xhr.send(form);
  });
}

/**
 * Open a named-event SSE connection to /query and stream tokens + sources.
 *
 * The backend sends three event types:
 *   event: sources  data: [{"source":"file.pdf","page":2}, ...]
 *   event: token    data: <token text>
 *   event: done     data: [DONE]
 *
 * @param {string}   question
 * @param {(sources: Array<{source:string,page:number}>) => void} onSources
 * @param {(token: string) => void}  onToken
 * @param {() => void}               onDone
 * @param {(err: Error) => void}     onError
 * @param {string}   [collection="default"]
 * @returns {EventSource}  caller can call .close() to abort
 */
export function streamQuery(question, onSources, onToken, onDone, onError, collection = "default") {
  const url = `${BASE}/query?q=${encodeURIComponent(question)}&collection=${encodeURIComponent(collection)}`;
  const es = new EventSource(url);

  // Named event: sources
  es.addEventListener("sources", (e) => {
    try {
      const sources = JSON.parse(e.data);
      onSources(sources);
    } catch {
      // ignore parse error
    }
  });

  // Named event: token
  es.addEventListener("token", (e) => {
    onToken(e.data.replace(/\\n/g, "\n"));
  });

  // Named event: done
  es.addEventListener("done", () => {
    es.close();
    onDone();
  });

  // Fallback: connection-level error (e.g. server down)
  es.onerror = () => {
    es.close();
    onError(new Error("Stream connection lost."));
  };

  return es;
}
