import { Fragment, useEffect, useRef, useState } from "react";
import { Answer } from "./Answer";
import { ApiError, MEMORY_TURNS, remember, streamQuery, type QueryResponse, type Turn } from "./api";
import { Feedback } from "./Feedback";

// sessionStorage only: the key leaves with the tab and is never written to the build or localStorage.
const KEY_STORAGE = "rag-api-key";

interface Message {
  id: number;
  query: string;
  // The answer as it streams in; replaced by the verified `final` result.
  partial: string;
  result: QueryResponse | null;
  error: string;
}

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
      className="key-card"
      onSubmit={(e) => {
        e.preventDefault();
        if (key.trim()) onSave(key.trim());
      }}
    >
      <h1>Welcome to Knowledge OS</h1>
      <label htmlFor="api-key">API key</label>
      <input id="api-key" type="password" autoComplete="off" value={key} onChange={(e) => setKey(e.target.value)} />
      <p className="hint">Kept in this tab only and cleared when the tab closes.</p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <button type="submit" className="button">
        Save key
      </button>
    </form>
  );
}

export default function App() {
  const [apiKey, setApiKey] = useState(storedKey);
  const [keyError, setKeyError] = useState("");
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  // Sent with each question so a follow-up can be rewritten; "Clear chat" keeps it.
  const [memory, setMemory] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const nextId = useRef(0);
  const end = useRef<HTMLDivElement>(null);

  // A block body: newer browsers return a Promise from scrollIntoView, which must not become the effect's cleanup.
  useEffect(() => {
    end.current?.scrollIntoView?.({ block: "end" });
  }, [messages]);

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
    setMenuOpen(false);
  }

  function clearChat(alsoMemory: boolean) {
    setMessages([]);
    if (alsoMemory) setMemory([]);
    setMenuOpen(false);
  }

  async function ask(e?: { preventDefault(): void }) {
    e?.preventDefault();
    const q = query.trim();
    if (!q || loading) return;
    const id = nextId.current++;
    const update = (change: (m: Message) => Partial<Message>) =>
      setMessages((ms) => ms.map((m) => (m.id === id ? { ...m, ...change(m) } : m)));
    setMessages((ms) => [...ms, { id, query: q, partial: "", result: null, error: "" }]);
    setQuery("");
    setLoading(true);
    try {
      const result = await streamQuery(apiKey, q, memory, (text) => update((m) => ({ partial: m.partial + text })));
      update(() => ({ result, partial: "" }));
      setMemory((mem) => remember(mem, q, result));
    } catch (err) {
      const apiError = err instanceof ApiError ? err : new ApiError(0, "Request failed.");
      update(() => ({ error: apiError.message }));
      if (apiError.status === 401) forgetKey(apiError.message);
    } finally {
      setLoading(false);
    }
  }

  const soon = "Available after the storage fix (Phase 15.0)";
  return (
    <div className={menuOpen ? "app menu-open" : "app"}>
      <aside className="side" aria-label="Actions">
        <div className="wordmark">
          Knowledge<span>.</span>os
        </div>
        <p className="group">Chat</p>
        <button type="button" className="act" disabled={loading || !messages.length} onClick={() => clearChat(false)}>
          Clear chat
        </button>
        <button
          type="button"
          className="act"
          disabled={loading || (!messages.length && !memory.length)}
          onClick={() => clearChat(true)}
        >
          Clear chat and memory
        </button>
        <p className="group">Documents</p>
        {/* shortcut: disabled until Phase 15.0 makes API ingest and delete persist (Interim rules, F-01/F-02). */}
        <button type="button" className="act" disabled title={soon}>
          Upload files <small>after 15.0</small>
        </button>
        <button type="button" className="act" disabled title={soon}>
          Clear database <small>after 15.0</small>
        </button>
        <div className="side-foot">
          <p>
            memory <b>{memory.length}/{MEMORY_TURNS}</b> turns
          </p>
          {apiKey && (
            <p>
              key set ·{" "}
              <button type="button" className="text-btn" aria-label="Change API key" onClick={() => forgetKey()}>
                change
              </button>
            </p>
          )}
        </div>
      </aside>
      <div className="backdrop" onClick={() => setMenuOpen(false)} />

      <main className="main">
        <header className="topbar">
          <button
            type="button"
            className="menu-btn"
            aria-label="Menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((o) => !o)}
          >
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M4 7h16M4 12h16M4 17h16" />
            </svg>
          </button>
          <span className="wordmark">
            Knowledge<span>.</span>os
          </span>
        </header>

        {/* Scrolls at the window edge, around the centred column, so opening sources never narrows it. */}
        <div className="scroll">
          <div className="column chat">
            {!apiKey ? (
              <KeyForm error={keyError} onSave={saveKey} />
            ) : (
              <>
                {messages.length === 0 && (
                  <div className="empty">
                    <h1>Ask your documents.</h1>
                    <p className="hint">Answers come only from your documents, with the passages they used.</p>
                  </div>
                )}
                {messages.map((m) => (
                  <Fragment key={m.id}>
                    <p className="question">{m.query}</p>
                    <div className="reply">
                      {m.result ? (
                        <Answer result={m.result}>
                          <Feedback
                            key={m.result.query_id}
                            apiKey={apiKey}
                            requestId={m.result.query_id}
                            onUnauthorized={forgetKey}
                          />
                        </Answer>
                      ) : (
                        m.partial && (
                          <section aria-label="Answer so far">
                            <p className="answer-text">
                              {m.partial}
                              {!m.error && <span className="caret" aria-hidden="true" />}
                            </p>
                          </section>
                        )
                      )}
                      {!m.result && !m.error && (
                        <p className="meta" aria-live="polite">
                          {m.partial ? "checking citations…" : "searching the documents…"}
                        </p>
                      )}
                      {m.error && (
                        <p className="error" role="alert">
                          {m.error}
                        </p>
                      )}
                    </div>
                  </Fragment>
                ))}
                <div ref={end} />
              </>
            )}
          </div>
        </div>

        {apiKey && (
          <form className="column composer" onSubmit={ask}>
            <label htmlFor="query" className="sr-only">
              Question
            </label>
            <textarea
              id="query"
              rows={1}
              maxLength={2000}
              placeholder="Ask a question…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) ask(e);
              }}
            />
            <button type="submit" className="button" disabled={loading || !query.trim()}>
              Ask
            </button>
          </form>
        )}
      </main>
    </div>
  );
}
