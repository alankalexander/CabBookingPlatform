"use client";
import { useState } from "react";
import { toast } from "../lib/toast";

// Address search through OpenStreetMap Nominatim (free, fair-use: keep it to manual searches)
export default function AddressSearch({ label, onPick }) {
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  async function search(e) {
    e.preventDefault();
    if (q.trim().length < 3) return toast("Type at least 3 characters", "info");
    setLoading(true);
    try {
      const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(q)}`);
      const data = await r.json();
      setResults(data);
      if (!data.length) toast("No places found. Try a more specific address.", "info");
    } catch { toast("Address search failed. Check your internet connection.", "error"); }
    finally { setLoading(false); }
  }

  return (
    <div>
      <form onSubmit={search} role="search" className="flex gap-2">
        <input className="border rounded p-2 flex-1 min-w-0 focus:outline-none focus:ring-2 focus:ring-black"
               aria-label={label} placeholder={label} value={q} onChange={e => setQ(e.target.value)} />
        <button disabled={loading} className="border rounded px-3 focus:outline-none focus:ring-2 focus:ring-black disabled:opacity-50">
          {loading ? "..." : "Search"}
        </button>
      </form>
      {results.length > 0 && (
        <ul className="border rounded mt-1 bg-white text-sm max-h-48 overflow-auto">
          {results.map(p => (
            <li key={p.place_id}>
              <button type="button" className="text-left w-full px-3 py-2 hover:bg-gray-100 focus:bg-gray-100 focus:outline-none"
                      onClick={() => { onPick([parseFloat(p.lat), parseFloat(p.lon)]); setResults([]); setQ(p.display_name.split(",").slice(0, 2).join(",")); }}>
                {p.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}