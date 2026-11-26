import { FormEvent, useState } from "react";
import { ask, ChatResponse } from "./api";

type Turn = { question: string; reply?: ChatResponse; error?: string };

const EXAMPLES = [
  "Which snacks are vegan and gluten free?",
  "Is the Vitamin C Serum in stock in Rotterdam?",
  "What do I pay for the cleanser with the discount?",
];

export default function App() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function send(question: string) {
    if (!question.trim() || busy) return;
    setBusy(true);
    setInput("");
    setTurns((t) => [...t, { question }]);
    try {
      const reply = await ask(question, sessionId);
      setSessionId(reply.session_id);
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, reply } : turn)));
    } catch (err) {
      const error = err instanceof Error ? err.message : "Something went wrong";
      setTurns((t) => t.map((turn, i) => (i === t.length - 1 ? { ...turn, error } : turn)));
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  return (
    <main className="page">
      <header>
        <h1>Commerce assistant</h1>
        <p>Answers come from the product catalog. Each reply shows the tools the agent used.</p>
      </header>

      <section className="chat" aria-live="polite">
        {turns.length === 0 && (
          <div className="examples">
            {EXAMPLES.map((q) => (
              <button key={q} onClick={() => void send(q)}>{q}</button>
            ))}
          </div>
        )}
        {turns.map((turn, i) => (
          <article key={i} className="turn">
            <p className="question">{turn.question}</p>
            {turn.error && <p className="error">{turn.error}</p>}
            {!turn.reply && !turn.error && <p className="pending">Thinking…</p>}
            {turn.reply && (
              <>
                <p className="answer">{turn.reply.answer}</p>
                <details>
                  <summary>
                    {turn.reply.tool_calls.length} tool call(s), {turn.reply.latency_s.toFixed(1)} s
                    {turn.reply.flags.length > 0 && <span className="flag"> · guardrail triggered</span>}
                  </summary>
                  <ul>
                    {turn.reply.tool_calls.map((c, j) => (
                      <li key={j}><code>{c.tool}({JSON.stringify(c.args)})</code></li>
                    ))}
                    {turn.reply.flags.map((f, j) => (
                      <li key={`f${j}`} className="flag"><code>{JSON.stringify(f)}</code></li>
                    ))}
                  </ul>
                </details>
              </>
            )}
          </article>
        ))}
      </section>

      <form onSubmit={onSubmit} className="composer">
        <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask about a product, price, stock or promotion" maxLength={1000} />
        <button type="submit" disabled={busy || !input.trim()}>Send</button>
      </form>
    </main>
  );
}
