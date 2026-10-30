import { useState, type ReactNode } from "react";
import type { QueryResponse } from "./api";
import { Icon } from "./Icon";

// Answer, reasons, claims and filenames come from documents and the LLM: render as text only, never as HTML.
function Verdict({ result }: { result: QueryResponse }) {
  if (result.outcome === "abstain" || result.outcome === "empty") {
    return (
      <div className="banner abstain" role="status">
        <strong>Not answered.</strong>{" "}
        {result.outcome === "empty"
          ? "Nothing relevant was found in the documents."
          : "The documents do not contain enough to answer this."}
        {result.sufficiency?.reason && <p className="reason">{result.sufficiency.reason}</p>}
      </div>
    );
  }
  // Cached answers keep their original confidence, so check it as well as the outcome.
  if (result.outcome === "answer_low_confidence" || result.confidence === "low") {
    const claims = result.citation_check?.unsupported_claims ?? [];
    return (
      <div className="banner low" role="status">
        <strong>Low confidence.</strong> Not every claim could be verified against the sources.
        {claims.length > 0 && (
          <ul>
            {claims.map((claim, i) => (
              <li key={i}>{claim}</li>
            ))}
          </ul>
        )}
      </div>
    );
  }
  return null;
}

/** The answer as plain text, with each [SOURCE N] marker shown as a small numbered badge. */
export function AnswerText({ text }: { text: string }) {
  return (
    <p className="answer-text">
      {text.split(/\[SOURCE (\d+)\]/).map((part, i) =>
        i % 2 ? (
          <span key={i} className="cite" title={`Source ${part}`}>
            {part}
          </span>
        ) : (
          part
        ),
      )}
    </p>
  );
}

/** `children`: the feedback controls, shown in the answer's footer. */
export function Answer({ result, children }: { result: QueryResponse; children?: ReactNode }) {
  const [showSources, setShowSources] = useState(false);
  const answered = result.outcome !== "abstain" && result.outcome !== "empty";
  const count = result.chunks.length;
  return (
    <section className="answer" aria-label="Answer">
      <Verdict result={result} />
      {answered && <AnswerText text={result.answer} />}
      <div className="answer-meta">
        {answered && result.confidence === "high" && <span className="badge ok">High confidence</span>}
        {count > 0 && (
          <button type="button" className="chip" aria-expanded={showSources} onClick={() => setShowSources((s) => !s)}>
            <Icon name="file" />
            {count} {answered ? (count === 1 ? "source" : "sources") : "documents searched"}
            <Icon name="down" className={showSources ? "flip" : undefined} />
          </button>
        )}
        <span className="spacer" />
        <span className="latency">
          {result.outcome === "cached" && "From cache · "}
          {(result.latency_ms / 1000).toFixed(1)} s
        </span>
        {children}
      </div>
      {showSources && (
        <ul className="sources">
          {result.chunks.map((chunk) => (
            <li key={chunk.n} className={chunk.cited ? "cited" : undefined}>
              <span className="n">{chunk.n}</span>
              <div>
                <div className="file">
                  {chunk.source}
                  {chunk.page != null && ` · page ${chunk.page}`}
                </div>
                <span className="snippet">{chunk.snippet}</span>
              </div>
              {chunk.cited && (
                <span className="cited-mark">
                  <Icon name="check" />
                  cited
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
