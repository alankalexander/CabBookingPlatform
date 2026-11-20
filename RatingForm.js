"use client";
import { useState } from "react";
import { api } from "../lib/api";
import { toast } from "../lib/toast";

const TAGS = {
  driver: ["Polite", "Safe driving", "Clean car", "On time", "Good route"],
  rider: ["Polite", "On time", "Easy pickup", "Respectful"],
};
const LABELS = ["", "Poor", "Below average", "Okay", "Good", "Excellent"];

// target = who is being rated: "driver" (by the rider) or "rider" (by the driver)
export default function RatingForm({ rideId, target = "driver", onDone }) {
  const [rating, setRating] = useState(0);
  const [hover, setHover] = useState(0);
  const [tags, setTags] = useState([]);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const shown = hover || rating;

  const toggle = t => setTags(l => (l.includes(t) ? l.filter(x => x !== t) : [...l, t]));

  async function submit() {
    if (!rating) return toast("Please choose a star rating first", "info");
    setBusy(true);
    try {
      const text = [tags.join(", "), comment.trim()].filter(Boolean).join(". ").slice(0, 300);
      await api(`/api/rides/${rideId}/review`, { method: "POST", body: { rating, comment: text } });
      toast("Thanks for your review!", "success");
      onDone && onDone({ rating, comment: text });
    } catch {} finally { setBusy(false); }
  }

  return (
    <div>
      <p className="font-medium mb-1">How was your {target}?</p>
      <div className="flex items-center gap-1 mb-1" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map(n => (
          <button key={n} type="button" aria-label={`${n} star${n > 1 ? "s" : ""}`} aria-pressed={rating === n}
                  className={`text-3xl leading-none focus:outline-none focus:ring-2 focus:ring-black rounded ${n <= shown ? "text-amber-500" : "text-gray-300"}`}
                  onMouseEnter={() => setHover(n)} onClick={() => setRating(n)}>★</button>
        ))}
        <span className="ml-2 text-sm text-gray-600">{LABELS[shown]}</span>
      </div>
      <div className="flex flex-wrap gap-2 my-2">
        {TAGS[target].map(t => (
          <button key={t} type="button" aria-pressed={tags.includes(t)} onClick={() => toggle(t)}
                  className={`text-xs border rounded-full px-3 py-1 focus:outline-none focus:ring-2 focus:ring-black ${tags.includes(t) ? "bg-black text-white" : ""}`}>
            {t}
          </button>
        ))}
      </div>
      <label className="sr-only" htmlFor={`cmt-${rideId}`}>Write a review</label>
      <textarea id={`cmt-${rideId}`} rows={3} maxLength={250} value={comment} onChange={e => setComment(e.target.value)}
                placeholder="Write a review (optional)"
                className="border rounded p-2 w-full text-sm focus:outline-none focus:ring-2 focus:ring-black" />
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-500">{comment.length}/250</span>
        <button type="button" disabled={busy} onClick={submit}
                className="bg-black text-white px-4 py-2 rounded disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black">
          {busy ? "Sending…" : "Submit review"}
        </button>
      </div>
    </div>
  );
}