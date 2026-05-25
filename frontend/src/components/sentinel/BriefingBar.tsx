import { useState } from "react";
import { postSentinelBriefing } from "@/lib/api";
import type { SentinelBriefingResponse } from "@/lib/types";

interface Props {
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
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground">
          Ask anything about the hazards visible on the map. Answers cite the
          actual event IDs.
        </p>
        {answer && (
          <button
            onClick={() => {
              setAnswer(null);
              setError("");
            }}
            className="text-[11px] text-muted-foreground hover:text-foreground"
          >
            clear
          </button>
        )}
      </div>
      <div className="space-y-3">
        {/* spacer to keep diff small below */}

        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") ask();
            }}
            placeholder="Ask anything about live hazards…  e.g. 'where should rescue be staged?'"
            className="flex-1 rounded-lg border border-border/60 bg-background/60 px-4 py-2.5 text-sm focus:border-cyan-500/60 focus:outline-none focus:ring-1 focus:ring-cyan-500/30"
          />
          <button
            onClick={() => ask()}
            disabled={loading || !question.trim()}
            className="rounded-lg bg-gradient-to-br from-cyan-500 to-cyan-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition-all hover:shadow-cyan-500/40 disabled:opacity-40"
          >
            {loading ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="inline-block h-2 w-2 animate-pulse rounded-full bg-white" />
                Thinking
              </span>
            ) : (
              "Brief →"
            )}
          </button>
        </div>

        {!answer && !loading && (
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTED.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setQuestion(s);
                  void ask(s);
                }}
                className="rounded-full border border-border/60 bg-secondary/30 px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-cyan-500/40 hover:bg-cyan-500/10 hover:text-cyan-200"
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-md border border-red-800/50 bg-red-950/30 p-2 text-xs text-red-300">
            {error}
          </div>
        )}

        {answer && (
          <div className="space-y-3 rounded-lg border border-cyan-700/30 bg-cyan-950/[0.15] p-4">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.18em]">
              <span className="rounded bg-cyan-500/20 px-2 py-0.5 font-bold text-cyan-300">
                {answer.provider}
              </span>
              <span className="text-muted-foreground">
                {answer.context_events} events in context
              </span>
            </div>
            <p className="whitespace-pre-wrap text-sm leading-relaxed text-cyan-50">
              {answer.answer}
            </p>
            {answer.citations.length > 0 && (
              <div className="flex flex-wrap gap-1.5 border-t border-cyan-800/30 pt-2">
                <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
                  citations:
                </span>
                {answer.citations.slice(0, 10).map((c) => (
                  <span
                    key={c.short_id}
                    className="rounded bg-cyan-900/40 px-1.5 py-0.5 font-mono text-[10px] text-cyan-200"
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
    </div>
  );
}
