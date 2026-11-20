import { io } from "socket.io-client";
import { toast } from "./toast";

export const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// sessionStorage = per browser tab, so one tab can be a rider and another a driver
export const getToken = () => (typeof window !== "undefined" ? sessionStorage.getItem("cab_token") : null);
export const setToken = t => sessionStorage.setItem("cab_token", t);
export const clearToken = () => sessionStorage.removeItem("cab_token");

// silent: true  -> no error toast (used for background polling)
export async function api(path, { method = "GET", body, silent = false } = {}) {
  let res;
  try {
    res = await fetch(BASE + path, {
      method,
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${getToken()}` },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    if (!silent) toast("Cannot reach the server. Is the backend running?", "error");
    throw new Error("network");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {}
    if (!silent) toast(msg, "error");
    throw new Error(msg);
  }
  return res.json();
}

export async function connectSocket() {
  return io(BASE, { auth: { token: getToken() } });
}

export async function downloadReceipt(rideId) {
  const res = await fetch(`${BASE}/api/rides/${rideId}/receipt`,
    { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) return toast("Receipt is not ready yet - try again in a moment.", "error");
  const blob = await res.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `receipt_${rideId}` + (blob.type.includes("pdf") ? ".pdf" : ".html");
  a.click();
  URL.revokeObjectURL(a.href);
}