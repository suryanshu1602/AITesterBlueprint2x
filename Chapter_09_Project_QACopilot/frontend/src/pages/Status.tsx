import { useEffect, useState } from "react";
import { fetchHealth, runIngest } from "../api/client";

type Health = {
  ok: boolean;
  groq_model: string;
  embed_model: string;
  rerank_model: string;
  qdrant: string;
  collections: Record<string, number>;
  data_paths: Record<string, string>;
};

const PIPELINES = ["selenium", "playwright", "testcases", "pdfs", "jira"] as const;

export default function Status() {
  const [h, setH] = useState<Health | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  const refresh = async () => {
    try { setH(await fetchHealth()); setErr(null); }
    catch (e: any) { setErr(String(e?.message ?? e)); }
  };

  useEffect(() => { void refresh(); }, []);

  const trigger = async (name: string, recreate = false) => {
    setRunning(name);
    try { await runIngest(name, recreate); await refresh(); }
    catch (e: any) { setErr(String(e?.message ?? e)); }
    setRunning(null);
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-5xl mx-auto p-5 space-y-4">
        <header>
          <h1 className="text-2xl font-bold">System status</h1>
          <p className="text-ink-soft text-[15px]">Health probe + per-collection counts + ingest controls.</p>
        </header>

        {err && (
          <div className="text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-3 text-sm">{err}</div>
        )}

        {h && (
          <>
            <section className="bg-white border border-gray-200 rounded-xl p-4 grid grid-cols-1 md:grid-cols-2 gap-2 text-[13px]">
              <KV k="Groq model" v={h.groq_model} />
              <KV k="Embed model" v={h.embed_model} />
              <KV k="Rerank model" v={h.rerank_model} />
              <KV k="Qdrant" v={h.qdrant} />
            </section>

            <section className="bg-white border border-gray-200 rounded-xl p-4">
              <h2 className="font-semibold mb-2">Collections</h2>
              <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
                {Object.entries(h.collections).map(([c, n]) => (
                  <div key={c} className="border border-gray-200 rounded-lg p-3">
                    <div className="font-mono text-[12px] text-ink-muted">{c}</div>
                    <div className="text-2xl font-bold text-accent-strong">{n}</div>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-white border border-gray-200 rounded-xl p-4">
              <h2 className="font-semibold mb-2">Ingest</h2>
              <div className="flex flex-wrap gap-2">
                {PIPELINES.map((p) => (
                  <div key={p} className="border border-gray-200 rounded-lg p-2 flex items-center gap-2">
                    <span className="font-mono text-[12px]">{p}</span>
                    <button onClick={() => trigger(p, false)} disabled={!!running}
                      className="text-[12px] px-2 py-1 rounded bg-accent-soft text-accent-strong border border-accent/30">
                      {running === p ? "running…" : "run"}
                    </button>
                    <button onClick={() => trigger(p, true)} disabled={!!running}
                      className="text-[12px] px-2 py-1 rounded bg-rose-50 text-rose-700 border border-rose-200">
                      recreate
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-white border border-gray-200 rounded-xl p-4">
              <h2 className="font-semibold mb-2">Data paths</h2>
              <div className="space-y-1 text-[12px] font-mono">
                {Object.entries(h.data_paths).map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-ink-muted w-36">{k}</span>
                    <span className="break-all">{v}</span>
                  </div>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

function KV({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-2">
      <span className="text-ink-muted w-32">{k}</span>
      <span className="font-mono break-all">{v}</span>
    </div>
  );
}
