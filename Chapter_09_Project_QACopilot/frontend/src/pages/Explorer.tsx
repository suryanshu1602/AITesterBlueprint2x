import { useState } from "react";
import { Search, ChevronDown, ChevronRight, Play } from "lucide-react";
import { explore } from "../api/client";
import type { Trace } from "../types";
import SourceFilter from "../components/SourceFilter";

export default function Explorer() {
  const [q, setQ] = useState("List P0 Blocker test cases for the Admin module");
  const [forced, setForced] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [trace, setTrace] = useState<Trace | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const run = async () => {
    setBusy(true);
    setErr(null);
    setTrace(null);
    try {
      const t = await explore({
        question: q,
        history: [],
        forced_collections: forced,
        mode: "answer",
      });
      setTrace(t);
    } catch (e: any) {
      setErr(String(e?.message ?? e));
    }
    setBusy(false);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-6xl mx-auto p-5 space-y-4">
        <header>
          <div className="flex items-center gap-2 text-accent-strong text-sm font-semibold mb-1">
            <Search size={16} /> RAG Explorer · debug every answer
          </div>
          <h1 className="text-2xl font-bold">Inspect the full retrieval pipeline.</h1>
          <p className="text-ink-soft text-[15px] max-w-2xl">
            Replay a question and see every stage — query rewrite, router decision,
            per-collection dense+sparse hits, RRF fusion, rerank, the exact context blocks
            sent to the LLM, and the final answer. No black boxes.
          </p>
        </header>

        <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3 shadow-sm">
          <textarea
            className="w-full border border-gray-300 rounded-lg p-2 text-sm"
            rows={2}
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          <div className="flex items-center gap-3 flex-wrap">
            <button
              onClick={run}
              disabled={busy}
              className="px-3 py-2 rounded-lg bg-accent-strong text-white inline-flex items-center gap-1.5 text-sm disabled:opacity-50"
            >
              <Play size={15} /> {busy ? "Running…" : "Run trace"}
            </button>
            <div className="flex-1 min-w-[260px]">
              <SourceFilter forced={forced} onChange={setForced} />
            </div>
          </div>
        </div>

        {err && (
          <div className="text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3 text-sm">
            {err}
          </div>
        )}

        {trace && <TraceView trace={trace} />}
      </div>
    </div>
  );
}

function TraceView({ trace }: { trace: Trace }) {
  return (
    <div className="space-y-3">
      <Stage num="01" title="Query Rewrite" defaultOpen>
        <KV k="Original" v={trace.query.original} mono />
        <KV k="Rewritten" v={trace.query.rewritten} mono />
        {trace.query.history.length > 0 && (
          <details className="mt-2">
            <summary className="text-[12px] text-ink-muted cursor-pointer">history ({trace.query.history.length} turns)</summary>
            <pre className="text-[12px] mt-1 whitespace-pre-wrap">
              {trace.query.history.map((t, i) => `${i + 1}. ${t.role}: ${t.content}`).join("\n")}
            </pre>
          </details>
        )}
      </Stage>

      <Stage num="02" title="Router Decision" defaultOpen>
        <div className="flex flex-wrap gap-1.5 mb-1.5">
          {trace.router.collections.map((c) => (
            <span key={c} className="text-[12px] px-2 py-0.5 rounded-full bg-accent-soft text-accent-strong border border-accent/30 font-semibold">
              {c}
            </span>
          ))}
        </div>
        <div className="text-[13px] text-ink-soft italic">{trace.router.reason || "(no reason returned)"}</div>
      </Stage>

      <Stage num="03" title="Per-Collection Hits (dense / sparse / fused)">
        <div className="space-y-3">
          {Object.entries(trace.per_collection).map(([col, data]) => (
            <div key={col} className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="bg-surface-card px-3 py-2 text-[13px] font-semibold">{col}</div>
              <div className="grid grid-cols-1 md:grid-cols-3 divide-x divide-gray-200">
                <HitList title="Dense" hits={data.dense_hits as any} />
                <HitList title="Sparse" hits={data.sparse_hits as any} />
                <HitList title="Fused (RRF)" hits={data.fused as any} keyField="rrf_score" />
              </div>
            </div>
          ))}
        </div>
      </Stage>

      <Stage num="04" title="Rerank (cross-encoder)" defaultOpen>
        <table className="w-full text-[13px]">
          <thead>
            <tr className="text-left text-ink-muted text-[11px] uppercase tracking-wider">
              <th className="py-1.5 pr-2">#</th>
              <th className="py-1.5 pr-2">chunk_id</th>
              <th className="py-1.5 pr-2">collection</th>
              <th className="py-1.5 pr-2">rerank</th>
              <th className="py-1.5 pr-2">fused→</th>
            </tr>
          </thead>
          <tbody>
            {trace.rerank.map((c) => (
              <tr key={c.chunk_id} className="border-t border-gray-100">
                <td className="py-1 pr-2 font-mono">{c.rerank_rank}</td>
                <td className="py-1 pr-2 font-mono break-all">{c.chunk_id}</td>
                <td className="py-1 pr-2">{(c.collection || c.payload?.collection) as string}</td>
                <td className="py-1 pr-2 font-mono text-accent-strong">{c.rerank_score?.toFixed(3)}</td>
                <td className="py-1 pr-2 font-mono text-ink-muted">{c.fused_rank}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Stage>

      <Stage num="05" title={`Final Context Blocks (${trace.context_blocks.length})`}>
        <div className="space-y-2">
          {trace.context_blocks.map((b) => (
            <div key={b.id} className="border border-gray-200 rounded-lg p-2.5 bg-surface-soft">
              <div className="flex items-center justify-between text-[12px] text-ink-muted mb-1.5">
                <span><span className="cite-chip">{b.id}</span> <span className="font-mono ml-1">{b.collection}</span></span>
                <span className="font-mono">{b.source}</span>
              </div>
              <pre className="text-[12px] whitespace-pre-wrap font-mono leading-snug max-h-60 overflow-y-auto">{b.text}</pre>
            </div>
          ))}
        </div>
      </Stage>

      {trace.llm && (
        <Stage num="06" title="LLM Call">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
            <div>
              <KV k="Model" v={trace.llm.model} mono />
              <KV k="Temperature" v={String(trace.llm.temperature)} mono />
              <KV k="Tokens" v={JSON.stringify(trace.llm.usage)} mono />
            </div>
            <div className="text-[11px] text-ink-muted">timings (ms)</div>
            <pre className="text-[11px] bg-surface-soft border border-gray-200 rounded p-2 col-span-full">
              {JSON.stringify(trace.timings_ms, null, 2)}
            </pre>
            <details className="col-span-full">
              <summary className="cursor-pointer text-[12px] text-ink-soft">system prompt</summary>
              <pre className="text-[11px] mt-1 whitespace-pre-wrap">{trace.llm.system}</pre>
            </details>
            <details className="col-span-full">
              <summary className="cursor-pointer text-[12px] text-ink-soft">user message (with context)</summary>
              <pre className="text-[11px] mt-1 whitespace-pre-wrap">{trace.llm.user}</pre>
            </details>
          </div>
        </Stage>
      )}

      {trace.answer && (
        <Stage num="07" title="Answer" defaultOpen>
          <pre className="text-[14px] whitespace-pre-wrap leading-relaxed">{trace.answer.text}</pre>
        </Stage>
      )}
    </div>
  );
}

function Stage({ num, title, children, defaultOpen }: { num: string; title: string; children: any; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(!!defaultOpen);
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-sm">
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center justify-between px-4 py-2.5">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[12px] text-accent-strong font-bold">{num}</span>
          <span className="font-semibold">{title}</span>
        </div>
        {open ? <ChevronDown size={17} /> : <ChevronRight size={17} />}
      </button>
      {open && <div className="border-t border-gray-100 px-4 py-3">{children}</div>}
    </div>
  );
}

function KV({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex gap-2 text-[13px] py-0.5">
      <span className="text-ink-muted w-24 shrink-0">{k}</span>
      <span className={mono ? "font-mono break-all" : ""}>{v}</span>
    </div>
  );
}

function HitList({ title, hits, keyField = "score" }: { title: string; hits: any[]; keyField?: string }) {
  return (
    <div className="p-2.5">
      <div className="text-[11px] uppercase tracking-wider text-ink-muted mb-1">{title}</div>
      <div className="space-y-1">
        {hits.slice(0, 8).map((h, i) => (
          <div key={i} className="text-[12px] flex items-center gap-2">
            <span className="font-mono text-ink-muted w-5">{i + 1}</span>
            <span className="font-mono text-accent-strong w-12">{(h[keyField] ?? 0).toFixed?.(3) ?? h[keyField]}</span>
            <span className="font-mono text-ink truncate" title={h.chunk_id}>{h.chunk_id}</span>
          </div>
        ))}
        {hits.length === 0 && <div className="text-[12px] text-ink-muted italic">none</div>}
      </div>
    </div>
  );
}
