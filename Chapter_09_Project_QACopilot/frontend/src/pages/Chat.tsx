import { useRef, useState } from "react";
import { Send, StopCircle, Sparkles } from "lucide-react";
import { chatStream } from "../api/client";
import type { Source, Turn } from "../types";
import SourceFilter from "../components/SourceFilter";
import SourcePanel from "../components/SourcePanel";
import MarkdownAnswer from "../components/MarkdownAnswer";

type Meta = { rewritten: string; router: { collections: string[]; reason: string }; timings_ms: Record<string, number> };

type DisplayTurn = Turn & { meta?: Meta; sources?: Source[]; streaming?: boolean };

export default function Chat() {
  const [turns, setTurns] = useState<DisplayTurn[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [forced, setForced] = useState<string[] | null>(null);
  const [mode, setMode] = useState<"answer" | "generate">("answer");
  const abortRef = useRef<AbortController | null>(null);

  const send = async () => {
    const q = input.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);

    const history: Turn[] = turns
      .filter((t) => !t.streaming)
      .map(({ role, content }) => ({ role, content }));

    setTurns((prev) => [
      ...prev,
      { role: "user", content: q },
      { role: "assistant", content: "", streaming: true },
    ]);

    const ac = new AbortController();
    abortRef.current = ac;

    const updateLast = (patch: Partial<DisplayTurn>) =>
      setTurns((prev) => {
        if (prev.length === 0) return prev;
        const idx = prev.length - 1;
        const last = prev[idx];
        if (!last.streaming) return prev;
        const next = prev.slice();
        next[idx] = { ...last, ...patch };
        return next;
      });

    const appendToLast = (piece: string) =>
      setTurns((prev) => {
        if (prev.length === 0) return prev;
        const idx = prev.length - 1;
        const last = prev[idx];
        if (!last.streaming) return prev;
        const next = prev.slice();
        next[idx] = { ...last, content: last.content + piece };
        return next;
      });

    await chatStream(
      { question: q, history, forced_collections: forced, mode },
      {
        onMeta: (meta) => updateLast({ meta }),
        onSources: (sources) => updateLast({ sources }),
        onToken: (piece) => appendToLast(piece),
        onDone: () => updateLast({ streaming: false }),
        onError: (err) =>
          setTurns((prev) => {
            if (prev.length === 0) return prev;
            const idx = prev.length - 1;
            const last = prev[idx];
            if (!last.streaming) return prev;
            const next = prev.slice();
            next[idx] = {
              ...last,
              content: last.content + `\n\n_error: ${err}_`,
              streaming: false,
            };
            return next;
          }),
      },
      ac.signal,
    );
    setBusy(false);
  };

  const stop = () => {
    abortRef.current?.abort();
    setBusy(false);
  };

  const lastSources =
    [...turns].reverse().find((t) => t.role === "assistant" && t.sources)?.sources ?? [];

  return (
    <div className="h-full grid grid-cols-1 md:grid-cols-[1fr_360px] gap-4 max-w-7xl mx-auto p-4 overflow-hidden">
      <section className="flex flex-col bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {turns.length === 0 && <Welcome onPick={(q) => setInput(q)} />}
          {turns.map((t, i) => (
            <Bubble key={i} turn={t} />
          ))}
        </div>
        <div className="border-t border-gray-200 p-3 bg-surface-soft">
          <div className="flex items-center gap-2 mb-2 text-[12px]">
            <button
              className={`px-2 py-1 rounded border ${
                mode === "answer"
                  ? "bg-accent-soft border-accent/40 text-accent-strong font-semibold"
                  : "bg-white border-gray-200 text-ink-soft"
              }`}
              onClick={() => setMode("answer")}
            >
              Answer
            </button>
            <button
              className={`px-2 py-1 rounded border ${
                mode === "generate"
                  ? "bg-accent-soft border-accent/40 text-accent-strong font-semibold"
                  : "bg-white border-gray-200 text-ink-soft"
              }`}
              onClick={() => setMode("generate")}
            >
              Generate TC
            </button>
            <span className="text-ink-muted ml-auto">⌘⏎ to send</span>
          </div>
          <div className="flex gap-2">
            <textarea
              className="flex-1 border border-gray-300 rounded-lg p-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent/40"
              rows={2}
              placeholder="Ask about Selenium / Playwright code, VWO test cases, PRDs, or JIRA bugs…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") send();
              }}
              disabled={busy}
            />
            {busy ? (
              <button
                onClick={stop}
                className="px-3 py-2 rounded-lg bg-rose-500 text-white inline-flex items-center gap-1.5 text-sm"
              >
                <StopCircle size={16} /> Stop
              </button>
            ) : (
              <button
                onClick={send}
                className="px-3 py-2 rounded-lg bg-accent-strong text-white inline-flex items-center gap-1.5 text-sm hover:bg-accent transition"
              >
                <Send size={16} /> Send
              </button>
            )}
          </div>
        </div>
      </section>

      <aside className="overflow-y-auto pr-1 space-y-3">
        <SourceFilter forced={forced} onChange={setForced} />
        <div>
          <h3 className="text-[12px] uppercase tracking-wider text-ink-muted px-1 mb-2">
            Sources for last answer
          </h3>
          <SourcePanel sources={lastSources} />
        </div>
      </aside>
    </div>
  );
}

function Bubble({ turn }: { turn: DisplayTurn }) {
  if (turn.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-accent-strong text-white rounded-2xl rounded-tr-sm px-4 py-2 text-[15px]">
          {turn.content}
        </div>
      </div>
    );
  }
  return (
    <div className="flex">
      <div className="max-w-[88%] bg-surface-card border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
        {turn.meta && (
          <div className="text-[11px] text-ink-muted mb-2 flex flex-wrap gap-2">
            <span>
              <strong>route:</strong> {turn.meta.router.collections.join(", ")}
            </span>
            <span title={turn.meta.router.reason} className="italic truncate max-w-[280px]">
              {turn.meta.router.reason}
            </span>
            {turn.meta.timings_ms.search_ms != null && (
              <span className="font-mono">search {turn.meta.timings_ms.search_ms}ms</span>
            )}
            {turn.meta.timings_ms.rerank_ms != null && (
              <span className="font-mono">rerank {turn.meta.timings_ms.rerank_ms}ms</span>
            )}
          </div>
        )}
        {turn.content ? (
          <MarkdownAnswer text={turn.content} />
        ) : (
          <div className="text-ink-muted italic text-sm">retrieving…</div>
        )}
      </div>
    </div>
  );
}

function Welcome({ onPick }: { onPick: (q: string) => void }) {
  const examples = [
    "Show the BasePage waitForElement implementation",
    "How is the login fixture set up in Playwright?",
    "List P0 Blocker test cases for the Admin module",
    "What does the PRD say about login dashboard auth flow?",
    "Show open bugs related to login failures",
  ];
  return (
    <div className="max-w-xl mx-auto py-8">
      <div className="flex items-center gap-2 text-accent-strong mb-2">
        <Sparkles size={18} />
        <span className="font-semibold">QA Copilot</span>
      </div>
      <h1 className="text-2xl font-bold mb-1">Ask anything across your QA stack.</h1>
      <p className="text-ink-soft mb-5 text-[15px]">
        Selenium code, Playwright code, VWO test cases, PRDs and JIRA bugs — one query.
        Each answer is grounded in retrieved chunks and cited inline.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {examples.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="text-left text-sm border border-gray-200 rounded-lg p-3 hover:border-accent-strong hover:bg-accent-soft/50 transition"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
