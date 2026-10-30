import { useState, type FormEvent } from "react";
import { ApiError, postFeedback, type Rating } from "./api";
import { Icon } from "./Icon";

interface Props {
  apiKey: string;
  requestId: string;
  onUnauthorized: (message: string) => void;
}

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
      setStatus(text ? "Comment saved." : "Thanks, feedback recorded.");
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
      <span className="feedback">
        <button
          type="button"
          className="icon-btn"
          aria-label="Helpful"
          aria-pressed={rating === "up"}
          disabled={sending}
          onClick={() => send("up")}
        >
          <Icon name="thumb" />
        </button>
        <button
          type="button"
          className="icon-btn"
          aria-label="Not helpful"
          aria-pressed={rating === "down"}
          disabled={sending}
          onClick={() => send("down")}
        >
          <Icon name="thumb" className="flip" />
        </button>
      </span>
      <p className="feedback-status" aria-live="polite">
        {status}
        {rating && !commenting && !sending && (
          <button type="button" className="link" onClick={() => setCommenting(true)}>
            Add a comment
          </button>
        )}
      </p>
      {commenting && (
        <form className="comment" onSubmit={sendComment}>
          <label htmlFor={commentId}>Comment (optional)</label>
          <textarea id={commentId} rows={2} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
          <button type="submit" className="primary" disabled={sending}>
            {sending ? "Sending…" : "Send feedback"}
          </button>
        </form>
      )}
    </>
  );
}
