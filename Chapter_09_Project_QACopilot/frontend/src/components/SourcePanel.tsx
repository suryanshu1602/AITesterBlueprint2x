import type { Source } from "../types";

const COLLECTION_BADGE: Record<string, { label: string; cls: string }> = {
  selenium_code: { label: "Selenium", cls: "bg-amber-100 text-amber-800 border-amber-200" },
  playwright_code: { label: "Playwright", cls: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  vwo_testcases: { label: "Test Case", cls: "bg-cyan-100 text-cyan-800 border-cyan-200" },
  vwo_docs: { label: "PRD", cls: "bg-violet-100 text-violet-800 border-violet-200" },
  vwo_bugs: { label: "JIRA Bug", cls: "bg-rose-100 text-rose-800 border-rose-200" },
};

type Props = { sources: Source[] };

export default function SourcePanel({ sources }: Props) {
  if (!sources.length) {
    return (
      <div className="text-sm text-ink-muted italic px-3 py-4">
        Sources will appear here after the next answer.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {sources.map((s) => {
        const badge = COLLECTION_BADGE[s.collection] ?? { label: s.collection, cls: "bg-gray-100 text-gray-800 border-gray-200" };
        return (
          <div
            id={`source-${s.id}`}
            key={s.id}
            className="border border-gray-200 rounded-lg bg-white p-3 shadow-sm"
          >
            <div className="flex items-center justify-between gap-2 mb-2">
              <div className="flex items-center gap-2">
                <span className="cite-chip">{s.id}</span>
                <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${badge.cls}`}>
                  {badge.label}
                </span>
              </div>
              {s.rerank_score !== undefined && (
                <span className="text-[11px] text-ink-muted font-mono">
                  rerank {s.rerank_score.toFixed(3)}
                </span>
              )}
            </div>
            <div className="text-[12px] text-ink-soft font-mono break-all mb-1">{s.source}</div>
            <pre className="text-[12px] text-ink whitespace-pre-wrap font-mono leading-snug max-h-40 overflow-y-auto bg-surface-soft border border-gray-100 rounded p-2">
              {s.preview}
            </pre>
          </div>
        );
      })}
    </div>
  );
}
