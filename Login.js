"use client";
import { useEffect, useState } from "react";
import { api, setToken, getToken } from "../lib/api";

export default function Login({ role, onDone }) {
  const [mode, setMode] = useState("login");
  const [f, setF] = useState({ email: "", password: "", name: "", vehicle_info: "", vehicle_number: "", license_no: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = k => e => setF({ ...f, [k]: e.target.value });

  useEffect(() => {   // restore session in this tab
    if (!getToken()) return;
    api("/api/auth/me", { silent: true }).then(u => u.role === role && onDone(u)).catch(() => {});
  }, []);

  async function submit(e) {
    e.preventDefault();
    setErr(""); setBusy(true);
    try {
      const res = mode === "login"
        ? await api("/api/auth/login", { method: "POST", body: { email: f.email, password: f.password }, silent: true })
        : await api("/api/auth/register", { method: "POST", body: { ...f, role }, silent: true });
      if (res.user.role !== role) { setErr(`This account is a ${res.user.role}. Use the ${res.user.role} page.`); return; }
      setToken(res.token);
      onDone(res.user);
    } catch (e2) { setErr(e2.message === "network" ? "Cannot reach the server. Is the backend running?" : e2.message); }
    finally { setBusy(false); }
  }

  const input = "border rounded p-2 w-full mb-2 focus:outline-none focus:ring-2 focus:ring-black";
  return (
    <form onSubmit={submit} className="max-w-sm mx-auto bg-white p-6 rounded shadow">
      <h1 className="font-bold mb-3 capitalize text-lg">{role} {mode === "login" ? "login" : "sign up"}</h1>
      {mode === "signup" && <input className={input} aria-label="Name" placeholder="Name" value={f.name} onChange={set("name")} />}
      {mode === "signup" && role === "driver" && <>
        <input className={input} aria-label="Vehicle" placeholder="Vehicle (e.g. White Swift)" value={f.vehicle_info} onChange={set("vehicle_info")} />
        <input className={input} aria-label="Vehicle number" placeholder="Vehicle number (e.g. KL-07-AB-1234)" value={f.vehicle_number} onChange={set("vehicle_number")} />
        <input className={input} aria-label="Licence number" placeholder="Driving licence number" value={f.license_no} onChange={set("license_no")} />
      </>}
      <input className={input} type="email" aria-label="Email" placeholder="Email" value={f.email} onChange={set("email")} required />
      <input className={input} type="password" aria-label="Password" placeholder="Password (min 6)" value={f.password} onChange={set("password")} required minLength={6} />
      {err && <p role="alert" className="text-red-600 text-sm mb-2">{err}</p>}
      <button disabled={busy} className="bg-black text-white px-4 py-2 rounded mr-2 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-black">
        {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
      </button>
      <button type="button" className="underline text-sm" onClick={() => setMode(mode === "login" ? "signup" : "login")}>
        {mode === "login" ? "New here? Sign up" : "Have an account? Sign in"}
      </button>
      <div className="mt-3 text-sm"><a className="underline" href="/reset">Forgot password?</a></div>
    </form>
  );
}