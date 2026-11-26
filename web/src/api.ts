export type ToolCall = { tool: string; args: Record<string, unknown> };
export type Flag = { type: string; [key: string]: unknown };

export type ChatResponse = {
  session_id: string;
  answer: string;
  tool_calls: ToolCall[];
  flags: Flag[];
  latency_s: number;
};

export async function ask(question: string, sessionId: string | null): Promise<ChatResponse> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, session_id: sessionId }),
  });
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}
