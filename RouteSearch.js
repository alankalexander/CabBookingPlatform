"use client";
import { useEffect, useState } from "react";

// Place suggestions from OpenStreetMap Nominatim (free; waits 600 ms after typing stops)
function useSuggest(query, enabled) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (!enabled || query.trim().length < 3) { setItems([]); setLoading(false); return; }
    setLoading(true);
    const t = setTimeout(async () => {
      try {
        const r = await fetch(`https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(query)}`);
        setItems(await r.json());
      } catch { setItems([]); }
      finally { setLoading(false); }
    }, 600);
    return () => clearTimeout(t);
  }, [query, enabled]);
  return { items, loading, clear: () => setItems([]) };
}

function Field({ id, tag, tagColor, placeholder, value, onPick, onClear }) {
  const [text, setText] = useState(value || "");
  const [typing, setTyping] = useState(false);
  const [open, setOpen] = useState(false);
  useEffect(() => { setText(value || ""); setTyping(false); }, [value]);
  const { items, loading, clear } = useSuggest(text, typing);

  function choose(p) {
    onPick([parseFloat(p.lat), parseFloat(p.lon)], p.display_name.split(",").slice(0, 3).join(","));
    clear(); setOpen(false); setTyping(false);
  }

  return (
    <div className="relative">
      <div className="flex items-center border-2 rounded bg-white focus-within:border-black">
        <label htmlFor={id} className={`px-3 py-2 text-xs font-bold text-white rounded-l ${tagColor}`}>{tag}</label>
        <input id={id} value={text} placeholder={placeholder} autoComplete="off"
               onChange={e => { setText(e.target.value); setTyping(true); setOpen(true); }}
               onFocus={() => setOpen(true)}
               onBlur={() => setTimeout(() => setOpen(false), 150)}
               onKeyDown={e => { if (e.key === "Enter" && items[0]) { e.preventDefault(); choose(items[0]); } }}
               className="flex-1 min-w-0 px-3 py-2 text-sm focus:outline-none" />
        {text && (
          <button type="button" aria-label={`Clear ${tag}`}
                  onClick={() => { setText(""); setTyping(false); clear(); onClear(); }}
                  className="px-3 text-gray-400 hover:text-black">x</button>
        )}
      </div>
      {open && typing && (loading || items.length > 0) && (
        <ul role="listbox" className="absolute left-0 right-0 top-full mt-1 bg-white border rounded shadow-lg text-sm max-h-56 overflow-auto z-[1100]">
          {loading && <li className="px-3 py-2 text-gray-500">Searching...</li>}
          {items.map(p => (
            <li key={p.place_id} role="option">
              <button type="button" onMouseDown={e => e.preventDefault()} onClick={() => choose(p)}
                      className="text-left w-full px-3 py-2 hover:bg-gray-100 focus:bg-gray-100 focus:outline-none">
                {p.display_name}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function RouteSearch({ pickupLabel, dropLabel, onPickup, onDrop, onSwap, onMyLocation, onClear }) {
  return (
    <div className="bg-white rounded shadow p-3 mb-3 border-2 border-black" role="search" aria-label="Route search">
      <p className="font-bold mb-2">Where to? Type a place in each box</p>
      <div className="flex items-center gap-2">
        <div className="flex-1 flex flex-col gap-2">
          <Field id="from" tag="FROM" tagColor="bg-green-600" placeholder="Type the starting place"
                 value={pickupLabel} onPick={onPickup} onClear={() => onPickup(null, "")} />
          <Field id="to" tag="TO" tagColor="bg-red-600" placeholder="Type the destination"
                 value={dropLabel} onPick={onDrop} onClear={() => onDrop(null, "")} />
        </div>
        <button type="button" onClick={onSwap} aria-label="Swap start and destination" title="Swap"
                className="border-2 rounded px-3 py-6 text-xl hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-black">
          &#8645;
        </button>
      </div>
      <div className="flex flex-wrap gap-4 mt-2 text-sm">
        <button type="button" className="underline" onClick={onMyLocation}>Use my current location as start</button>
        <button type="button" className="underline text-gray-600" onClick={onClear}>Clear route</button>
      </div>
    </div>
  );
}