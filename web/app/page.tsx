"use client";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Step =
  | { kind: "tool_call"; name: string; args: Record<string, unknown> }
  | { kind: "tool_result"; name: string; content: string };

type Usage = {
  model: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_usd: number;
};

export default function Home() {
  const [q, setQ] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [answer, setAnswer] = useState("");
  const [usage, setUsage] = useState<Usage | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask() {
    if (!q.trim() || loading) return;
    setSteps([]);
    setAnswer("");
    setUsage(null);
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
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split("\n\n");
        buf = parts.pop() ?? ""; // keep the trailing partial event
        for (const part of parts) {
          if (!part.startsWith("data: ")) continue;
          let evt: any;
          try {
            evt = JSON.parse(part.slice(6));
          } catch {
            continue;
          }
          if (evt.type === "tool_call")
            setSteps((s) => [...s, { kind: "tool_call", name: evt.name, args: evt.args }]);
          else if (evt.type === "tool_result")
            setSteps((s) => [...s, { kind: "tool_result", name: evt.name, content: evt.content }]);
          else if (evt.type === "token") setAnswer((a) => a + evt.content);
          else if (evt.type === "usage") setUsage(evt as Usage);
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: "40px auto", padding: "0 16px" }}>
      <h1>Ops Copilot</h1>
      <p className="muted">Describe an alert or symptom; the agent shows its steps, then answers.</p>
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

      {steps.length > 0 && (
        <section className="trace">
          <div className="trace-title">Agent trace</div>
          {steps.map((s, i) =>
            s.kind === "tool_call" ? (
              <div key={i} className="step step-call">
                <span className="badge">tool</span>
                <code>
                  {s.name}({Object.entries(s.args).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", ")})
                </code>
              </div>
            ) : (
              <details key={i} className="step step-result">
                <summary>
                  <span className="badge badge-ok">result</span> {s.name}
                </summary>
                <pre>{s.content}</pre>
              </details>
            )
          )}
        </section>
      )}

      {answer && (
        <article className="answer">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{answer}</ReactMarkdown>
        </article>
      )}

      {usage && (
        <div className="usage">
          {usage.model} · {usage.input_tokens} in / {usage.output_tokens} out (
          {usage.total_tokens} tokens) · ~${usage.cost_usd.toFixed(6)}
        </div>
      )}
    </main>
  );
}
