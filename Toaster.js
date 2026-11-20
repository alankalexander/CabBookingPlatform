"use client";
import { useEffect, useState } from "react";
import { onToast } from "../lib/toast";

export default function Toaster() {
  const [items, setItems] = useState([]);
  useEffect(() => onToast(t => {
    setItems(l => [...l, t]);
    setTimeout(() => setItems(l => l.filter(x => x.id !== t.id)), 4500);
  }), []);
  const color = { error: "bg-red-600", success: "bg-green-600", info: "bg-gray-800" };
  return (
    <div aria-live="polite" role="status"
         className="fixed bottom-4 left-4 right-4 sm:left-auto sm:w-80 z-[2000] space-y-2">
      {items.map(t => (
        <div key={t.id} className={`${color[t.type] || color.info} text-white text-sm rounded px-4 py-3 shadow-lg`}>
          {t.message}
        </div>
      ))}
    </div>
  );
}