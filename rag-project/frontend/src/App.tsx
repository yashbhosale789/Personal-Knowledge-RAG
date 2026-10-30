import { useState, type FormEvent } from "react";
import { Answer } from "./Answer";
import { ApiError, postQuery, type QueryResponse } from "./api";
import { Feedback } from "./Feedback";

// sessionStorage only: the key leaves with the tab and is never written to the build or localStorage.
const KEY_STORAGE = "rag-api-key";

function storedKey(): string {
  try {
    return sessionStorage.getItem(KEY_STORAGE) ?? "";
  } catch {
    return "";
  }
}

function KeyForm({ error, onSave }: { error: string; onSave: (key: string) => void }) {
  const [key, setKey] = useState("");
  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        if (key.trim()) onSave(key.trim());
      }}
    >
      <label htmlFor="api-key">API key</label>
      <input id="api-key" type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} />
      <p className="hint">Kept in this tab only and cleared when the tab closes.</p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="submit">Save key</button>
    </form>
  );
}

export default function App() {
  const [apiKey, setApiKey] = useState(storedKey);
  const [keyError, setKeyError] = useState("");
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function saveKey(key: string) {
    try {
      sessionStorage.setItem(KEY_STORAGE, key);
    } catch {
      // Storage blocked: the key still works until the page reloads.
    }
    setKeyError("");
    setApiKey(key);
  }

  function forgetKey(message = "") {
    try {
      sessionStorage.removeItem(KEY_STORAGE);
    } catch {
      // Nothing stored.
    }
    setApiKey("");
    setKeyError(message);
    setResult(null);
    setError("");
  }

  async function ask(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q || loading) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      setResult(await postQuery(apiKey, q));
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError(0, "Request failed.");
      if (apiError.status === 401) forgetKey(apiError.message);
      else setError(apiError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main>
      <header>
        <h1>Knowledge OS</h1>
        {apiKey && (
          <button type="button" className="link" onClick={() => forgetKey()}>
            Forget key
          </button>
        )}
      </header>
      {!apiKey ? (
        <KeyForm error={keyError} onSave={saveKey} />
      ) : (
        <>
          <form className="card" onSubmit={ask}>
            <label htmlFor="query">Question</label>
            <textarea id="query" rows={3} maxLength={2000} value={query} onChange={(e) => setQuery(e.target.value)} />
            <button type="submit" disabled={loading || !query.trim()}>
              {loading ? "Searching…" : "Ask"}
            </button>
          </form>
          <div aria-live="polite">
            {loading && <p className="hint">Retrieving, generating and verifying citations. This can take about 10 seconds.</p>}
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
          </div>
          {result && (
            <>
              <Answer result={result} />
              <Feedback key={result.query_id} apiKey={apiKey} requestId={result.query_id} onUnauthorized={forgetKey} />
            </>
          )}
        </>
      )}
    </main>
  );
}
