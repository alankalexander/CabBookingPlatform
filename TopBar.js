"use client";
import { api, clearToken } from "../lib/api";
import { toast } from "../lib/toast";

export default function TopBar({ user }) {
  async function resend() {
    await api("/api/auth/send-verification", { method: "POST" });
    toast("Verification link sent (see the backend terminal if SMTP is not set up).", "success");
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 bg-white rounded shadow px-4 py-2 mb-3 text-sm">
      <span>
        👤 <b>{user.name}</b>{" "}
        <span className="text-xs bg-gray-200 rounded px-2 py-0.5 capitalize">{user.role}</span>
        {!user.email_verified && (
          <button className="ml-2 text-amber-700 underline" onClick={resend}>Email not verified - resend link</button>
        )}
      </span>
      <nav className="flex flex-wrap gap-4 items-center" aria-label="Account">
        <a className="underline" href="/history">History</a>
        <a className="underline" href="/profile">Profile</a>
        <button className="border rounded px-3 py-1 focus:outline-none focus:ring-2 focus:ring-black"
                onClick={() => { clearToken(); window.location.reload(); }}>
          Log out
        </button>
      </nav>
    </div>
  );
}