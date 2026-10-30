import { useState, type ReactNode } from "react";
import type { QueryResponse } from "./api";

// Answer, reasons, claims and filenames come from documents and the LLM: render as text only, never as HTML.
function Verdict({ result }: { result: QueryResponse }) {
  if (result.outcome === "abstain" || result.outcome === "empty") {
    return (
      <div className="note abstain" role="status">
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
      <div className="note low" role="status">
        <strong>Low confidence.</strong> Not every claim could be checked against the sources.
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

/** The answer as plain text, with each [SOURCE N] marker shown as a footnote number on the word before it. */
export function AnswerText({ text }: { text: string }) {
  return (
    <p className="answer-text">
      {text.split(/\s*\[SOURCE (\d+)\]/).map((part, i) =>
        i % 2 ? (
          <sup key={i} className="cite" title={`Source ${part}`}>
            {part}
          </sup>
        ) : (
          part
        ),
      )}
    </p>
  );
}

/** `children`: the feedback controls, shown on the answer's metadata line. */
export function Answer({ result, children }: { result: QueryResponse; children?: ReactNode }) {
  const [showSources, setShowSources] = useState(false);
  const answered = result.outcome !== "abstain" && result.outcome !== "empty";
  const count = result.chunks.length;
  return (
    <section className="answer" aria-label="Answer">
      <Verdict result={result} />
      {answered && <AnswerText text={result.answer} />}
      <div className="meta">
        {answered && result.confidence === "high" && <span className="verified">✓ verified</span>}
        {result.outcome === "cached" && <span>from cache</span>}
        <span>{(result.latency_ms / 1000).toFixed(1)} s</span>
        {count > 0 && (
          <button type="button" className="text-btn" aria-expanded={showSources} onClick={() => setShowSources((s) => !s)}>
            {showSources ? "hide " : ""}
            {count} {answered ? (count === 1 ? "source" : "sources") : "documents searched"}
          </button>
        )}
        {children}
      </div>
      {showSources && (
        <ol className="footnotes">
          {result.chunks.map((chunk) => (
            <li key={chunk.n} className={chunk.cited ? "cited" : undefined}>
              <span className="n">{chunk.n}</span>
              <span>
                {chunk.source}
                {chunk.page != null && `, p. ${chunk.page}`}
                <span className="snippet">{chunk.snippet}</span>
              </span>
              {chunk.cited && <span className="cited-mark">cited</span>}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
