"use client";
import { useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [q, setQ] = useState("");
  const [out, setOut] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask() {
    if (!q.trim() || loading) return;
    setOut("");
    setError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/agent/stream`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ question: q, thread_id: crypto.randomUUID() }),
      });
      if (!res.ok || !res.body) {
        throw new Error(`Request failed: ${res.status} ${res.statusText}`);
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of dec.decode(value).split("\n\n")) {
          if (line.startsWith("data: ") && !line.includes("[DONE]")) {
            setOut((p) => p + line.slice(6));
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 640, margin: "40px auto", padding: "0 16px" }}>
      <h1>Ops Copilot</h1>
      <p className="muted">Describe an alert or symptom; the agent streams its answer.</p>
      <textarea
        value={q}
        onChange={(e) => setQ(e.target.value)}
        rows={3}
        style={{ width: "100%" }}
        placeholder="e.g. Postgres connections are near max, what do I do?"
      />
      <div>
        <button onClick={ask} disabled={loading || !q.trim()}>
          {loading ? "Thinking…" : "Ask"}
        </button>
      </div>
      {error && <div className="error">{error}</div>}
      <pre style={{ whiteSpace: "pre-wrap", marginTop: 16 }}>{out}</pre>
    </main>
  );
}
