"use client";
import { useState } from "react";

export default function Home() {
  const [q, setQ] = useState("");
  const [out, setOut] = useState("");

  async function ask() {
    setOut("");
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/agent/stream`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ question: q, thread_id: crypto.randomUUID() }),
    });
    const reader = res.body!.getReader();
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
  }

  return (
    <main style={{ maxWidth: 640, margin: "40px auto", fontFamily: "system-ui" }}>
      <h1>Ops Copilot</h1>
      <textarea
        value={q}
        onChange={(e) => setQ(e.target.value)}
        rows={3}
        style={{ width: "100%" }}
        placeholder="Describe the alert or symptom"
      />
      <button onClick={ask}>Ask</button>
      <pre style={{ whiteSpace: "pre-wrap", marginTop: 16 }}>{out}</pre>
    </main>
  );
}
