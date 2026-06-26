import { deleteDocument } from "../api/client";

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
    <>
      <div className="px-4 py-2 flex items-center justify-between border-b border-outline-variant/30 mb-2">
        <span className="text-label-upper font-label-upper tracking-wider text-on-surface-variant">
          Indexed Documents
        </span>
        <label className="flex items-center gap-2 text-label-upper text-on-surface-variant cursor-pointer hover:text-on-surface transition-colors" title="Search across all documents at once">
          <input
            type="checkbox"
            checked={searchAll}
            onChange={(e) => onSearchAllChange(e.target.checked)}
            className="accent-secondary w-3 h-3 cursor-pointer"
          />
          <span>ALL</span>
        </label>
      </div>

      <div className="flex flex-col gap-1">
        {documents.map((doc) => {
          const isActive = doc.document_id === activeDocumentId && !searchAll;
          const activeClasses = isActive
            ? "bg-surface-container-highest text-secondary border-l-2 border-secondary"
            : "text-on-surface-variant hover:bg-surface-container-high border-l-2 border-transparent";

          return (
            <div
              key={doc.document_id}
              className={`group flex items-center justify-between px-4 py-3 text-label-upper font-label-upper tracking-wider transition-all duration-200 ease-in-out cursor-pointer ${activeClasses}`}
              onClick={() => onSelect(doc.document_id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => e.key === "Enter" && onSelect(doc.document_id)}
            >
              <div className="flex items-center gap-3 overflow-hidden flex-1">
                <span className="material-symbols-outlined text-lg flex-shrink-0">
                  {isActive ? "menu_book" : "description"}
                </span>
                <span className="truncate" title={doc.name}>
                  {doc.name}
                </span>
              </div>
              <button
                className="opacity-0 group-hover:opacity-100 text-on-surface-variant hover:text-error transition-all p-1 rounded-sm flex-shrink-0"
                onClick={(e) => handleDelete(e, doc.document_id)}
                title="Remove document"
              >
                <span className="material-symbols-outlined text-base">close</span>
              </button>
            </div>
          );
        })}
      </div>
    </>
  );
}
