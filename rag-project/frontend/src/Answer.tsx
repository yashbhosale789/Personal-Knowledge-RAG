import type { QueryResponse } from "./api";

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

export function Answer({ result }: { result: QueryResponse }) {
  const answered = result.outcome !== "abstain" && result.outcome !== "empty";
  return (
    <section className="answer" aria-label="Answer">
      <Verdict result={result} />
      {answered && <p className="answer-text">{result.answer}</p>}
      {result.chunks.length > 0 && (
        <>
          <h2>{answered ? "Sources" : "Documents searched"}</h2>
          <ul className="sources">
            {result.chunks.map((chunk) => (
              <li key={chunk.n} className={chunk.cited ? "cited" : undefined}>
                <strong>[SOURCE {chunk.n}]</strong> {chunk.source}
                {chunk.page != null && `, page ${chunk.page}`}
                {chunk.cited && " · cited"}
                <span className="snippet">{chunk.snippet}</span>
              </li>
            ))}
          </ul>
        </>
      )}
      <p className="meta">
        {result.outcome === "cached" && "From cache · "}
        {(result.latency_ms / 1000).toFixed(1)} s
      </p>
    </section>
  );
}
