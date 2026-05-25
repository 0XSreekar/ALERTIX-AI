import { useState } from "react";
import { postSentinelBriefing } from "@/lib/api";
import type { SentinelBriefingResponse } from "@/lib/types";

interface Props {
  /** event IDs currently visible on the globe — passed as RAG context */
  contextEventIds: string[];
}

const SUGGESTED = [
  "What's the worst hazard right now?",
  "Summarise threats in the Himalayas",
  "Any cascading risks I should know about?",
  "Which coastal states need attention?",
];

export default function BriefingBar({ contextEventIds }: Props) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [answer, setAnswer] = useState<SentinelBriefingResponse | null>(null);

  const ask = async (q?: string) => {
    const text = (q ?? question).trim();
    if (!text) return;
    setLoading(true);
    setError("");
    try {
      const res = await postSentinelBriefing(text, contextEventIds);
      setAnswer(res);
      if (!q) setQuestion("");
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3 rounded-lg border border-border bg-card/80 p-4 backdrop-blur">
      <div className="flex items-center justify-between text-xs">
        <h3 className="font-semibold uppercase tracking-wider text-muted-foreground">
          AI Briefing
        </h3>
        <span className="text-muted-foreground">
          context: {contextEventIds.length} events
        </span>
      </div>

      <div className="flex gap-2">
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") ask();
          }}
          placeholder="Ask anything about live hazards…"
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm focus:border-primary focus:outline-none"
        />
        <button
          onClick={() => ask()}
          disabled={loading || !question.trim()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {loading ? "…" : "Brief"}
        </button>
      </div>

      {!answer && (
        <div className="flex flex-wrap gap-1.5">
          {SUGGESTED.map((s) => (
            <button
              key={s}
              onClick={() => {
                setQuestion(s);
                void ask(s);
              }}
              className="rounded-full border border-border bg-secondary/40 px-3 py-1 text-xs text-muted-foreground hover:bg-secondary"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}

      {answer && (
        <div className="space-y-3 rounded-md border border-blue-700/30 bg-blue-950/20 p-3 text-sm">
          <div className="flex items-center gap-2 text-[11px] uppercase text-blue-300">
            <span className="rounded bg-blue-600/20 px-2 py-0.5 font-semibold">
              {answer.provider}
            </span>
            <span className="text-muted-foreground">
              grounded on {answer.context_events} events
            </span>
          </div>
          <p className="whitespace-pre-wrap leading-relaxed text-blue-50">
            {answer.answer}
          </p>
          {answer.citations.length > 0 && (
            <div className="flex flex-wrap gap-1.5 border-t border-blue-800/30 pt-2">
              {answer.citations.slice(0, 8).map((c) => (
                <span
                  key={c.short_id}
                  className="rounded bg-blue-900/30 px-1.5 py-0.5 font-mono text-[10px] text-blue-200"
                  title={c.title}
                >
                  {c.short_id}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
