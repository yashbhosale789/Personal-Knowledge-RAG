import { useState, type FormEvent } from "react";
import { ApiError, postFeedback, type Rating } from "./api";

interface Props {
  apiKey: string;
  requestId: string;
  onUnauthorized: (message: string) => void;
}

export function Feedback({ apiKey, requestId, onUnauthorized }: Props) {
  const [rating, setRating] = useState<Rating | null>(null);
  const [comment, setComment] = useState("");
  const [status, setStatus] = useState("");
  const [sending, setSending] = useState(false);

  async function send(e: FormEvent) {
    e.preventDefault();
    if (!rating) return;
    setSending(true);
    setStatus("");
    try {
      await postFeedback(apiKey, requestId, rating, comment.trim());
      setStatus("Feedback recorded. Sending again replaces it.");
    } catch (err) {
      const error = err instanceof ApiError ? err : new ApiError(0, "Feedback failed.");
      if (error.status === 401) return onUnauthorized(error.message);
      setStatus(error.status === 404 ? "This answer can no longer be rated (answers expire after 24 hours)." : error.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <form className="feedback" onSubmit={send}>
      <fieldset>
        <legend>Was this answer helpful?</legend>
        <div className="thumbs">
          <button type="button" aria-pressed={rating === "up"} onClick={() => setRating("up")}>
            👍 Helpful
          </button>
          <button type="button" aria-pressed={rating === "down"} onClick={() => setRating("down")}>
            👎 Not helpful
          </button>
        </div>
        <label htmlFor="comment">Comment (optional)</label>
        <textarea id="comment" rows={2} maxLength={1000} value={comment} onChange={(e) => setComment(e.target.value)} />
        <button type="submit" disabled={!rating || sending}>
          {sending ? "Sending…" : "Send feedback"}
        </button>
        <p aria-live="polite">{status}</p>
      </fieldset>
    </form>
  );
}
