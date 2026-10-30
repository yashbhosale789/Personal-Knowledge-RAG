import { useState, type FormEvent } from "react";
import { ApiError, postFeedback, type Rating } from "./api";

interface Props {
  apiKey: string;
  requestId: string;
  onUnauthorized: (message: string) => void;
}

// Lucide's thumbs-up outline; the "down" button rotates it.
const Thumb = () => (
  <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M7 10v12" />
    <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
  </svg>
);

/** Thumbs send the rating at once; an optional comment re-sends it (the API keeps the latest). */
export function Feedback({ apiKey, requestId, onUnauthorized }: Props) {
  const [rating, setRating] = useState<Rating | null>(null);
  const [commenting, setCommenting] = useState(false);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);

  async function send(chosen: Rating, text = "") {
    setRating(chosen);
    setSending(true);
    setStatus("");
    try {
      await postFeedback(apiKey, requestId, chosen, text);
      setStatus(text ? "comment saved" : "thanks");
      if (text) setCommenting(false);
    } catch (err) {
      const error = err instanceof ApiError ? err : new ApiError(0, "Feedback failed.");
      if (error.status === 401) return onUnauthorized(error.message);
      setStatus(error.status === 404 ? "This answer can no longer be rated (answers expire after 24 hours)." : error.message);
    } finally {
      setSending(false);
    }
  }

  function sendComment(e: FormEvent) {
    e.preventDefault();
    if (rating) send(rating, comment.trim());
  }

  const commentId = `comment-${requestId}`;
  return (
    <>
      <span className="feedback" role="group" aria-label="Was this answer helpful?">
        <button
          type="button"
          className="thumb"
          aria-label="Helpful"
          aria-pressed={rating === "up"}
          disabled={sending}
          onClick={() => send("up")}
        >
          <Thumb />
        </button>
        <button
          type="button"
          className="thumb down"
          aria-label="Not helpful"
          aria-pressed={rating === "down"}
          disabled={sending}
          onClick={() => send("down")}
        >
          <Thumb />
        </button>
      </span>
      <span aria-live="polite">{status}</span>
      {rating && !commenting && !sending && (
        <button type="button" className="text-btn" onClick={() => setCommenting(true)}>
          add a comment
        </button>
      )}
      {commenting && (
        <form className="comment" onSubmit={sendComment}>
          <label htmlFor={commentId}>Comment (optional)</label>
          <textarea id={commentId} rows={2} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
          <button type="submit" className="button" disabled={sending}>
            {sending ? "Sending…" : "Send feedback"}
          </button>
        </form>
      )}
    </>
  );
}
