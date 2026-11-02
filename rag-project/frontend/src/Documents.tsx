import { useRef, useState } from "react";
import { ApiError, deleteDocument, listDocuments, uploadDocument, type DocumentInfo } from "./api";

interface Props {
  apiKey: string;
  onUnauthorized: (message: string) => void;
}

/** Sidebar documents panel: the list loads when it is first opened. Names are rendered as text. */
export function Documents({ apiKey, onUnauthorized }: Props) {
  const [docs, setDocs] = useState<DocumentInfo[] | null>(null);
  const [working, setWorking] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const picker = useRef<HTMLInputElement>(null);

  // Runs one change (or none), then reloads the list; one at a time, as the API allows.
  async function run(label: string, change?: () => Promise<string>) {
    setWorking(label);
    setStatus("");
    setError("");
    try {
      if (change) setStatus(await change());
      setDocs(await listDocuments(apiKey));
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError(0, "Request failed.");
      if (apiError.status === 401) return onUnauthorized(apiError.message);
      setError(apiError.message);
    } finally {
      setWorking("");
    }
  }

  function upload(file: File | undefined) {
    if (picker.current) picker.current.value = ""; // picking the same file again still fires
    if (!file) return;
    run(`Indexing ${file.name}… a long document can take a few minutes.`, async () => {
      const chunks = await uploadDocument(apiKey, file);
      return `${file.name}: ${chunks} chunks indexed.`;
    });
  }

  function remove(name: string) {
    if (!window.confirm(`Delete ${name}? Its passages are removed from the knowledge base.`)) return;
    run(`Deleting ${name}…`, async () => {
      await deleteDocument(apiKey, name);
      return `${name} deleted.`;
    });
  }

  return (
    <details
      className="docs"
      onToggle={(e) => {
        if (e.currentTarget.open && docs === null && !working) run("Loading documents…");
      }}
    >
      <summary className="group">Documents</summary>
      <input
        ref={picker}
        type="file"
        accept=".pdf,application/pdf"
        hidden
        aria-label="PDF to upload"
        onChange={(e) => upload(e.target.files?.[0])}
      />
      <button type="button" className="act" disabled={!!working} onClick={() => picker.current?.click()}>
        Upload PDF
      </button>
      <p className="meta" aria-live="polite">
        {working || status}
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {docs && (
        <ul className="doc-list" aria-label="Documents">
          {docs.length === 0 && <li className="meta">No documents yet.</li>}
          {docs.map((d) => (
            <li key={d.name}>
              <span className="doc-name">{d.name}</span>
              <small>{d.chunks} chunks</small>
              <button
                type="button"
                className="text-btn"
                aria-label={`Delete ${d.name}`}
                disabled={!!working}
                onClick={() => remove(d.name)}
              >
                delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </details>
  );
}
