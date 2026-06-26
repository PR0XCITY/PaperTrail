import { deleteDocument } from "../api/client";

/**
 * Sidebar document list with:
 * - Active document highlighting
 * - Per-document delete button
 * - "Search All" toggle
 */
export default function DocumentList({
  documents,
  activeDocumentId,
  onSelect,
  onDelete,
  searchAll,
  onSearchAllChange,
}) {
  async function handleDelete(e, docId) {
    e.stopPropagation();
    if (!window.confirm("Remove this document from the index?")) return;
    try {
      await deleteDocument(docId);
      onDelete(docId);
    } catch (err) {
      alert(`Failed to delete: ${err.message}`);
    }
  }

  return (
    <div className="doc-list">
      <div className="doc-list-header">
        <h3 className="doc-list-title">Indexed Documents</h3>
        <label className="search-all-toggle" title="Search across all documents at once">
          <input
            type="checkbox"
            checked={searchAll}
            onChange={(e) => onSearchAllChange(e.target.checked)}
          />
          <span>All</span>
        </label>
      </div>

      <div className="doc-items">
        {documents.map((doc) => {
          const isActive = doc.document_id === activeDocumentId && !searchAll;
          return (
            <div
              key={doc.document_id}
              className={`doc-item ${isActive ? "doc-item--active" : ""}`}
              onClick={() => onSelect(doc.document_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onSelect(doc.document_id)}
              aria-label={`Select ${doc.name}`}
              aria-current={isActive ? "true" : undefined}
            >
              <div className="doc-item-icon">{isActive ? "📗" : "📑"}</div>
              <div className="doc-item-meta">
                <span className="doc-item-name" title={doc.name}>
                  {doc.name}
                </span>
                <span className="doc-item-stats">
                  {doc.pages}p · {doc.chunks} chunks
                </span>
              </div>
              <button
                className="doc-item-delete"
                onClick={(e) => handleDelete(e, doc.document_id)}
                title="Remove document"
                aria-label={`Remove ${doc.name}`}
              >
                ×
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
