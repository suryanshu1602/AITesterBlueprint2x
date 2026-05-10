import { useState } from "react";
import type { CollectionName } from "../types";

const ALL: { name: CollectionName; label: string; hint: string }[] = [
  { name: "selenium_code", label: "Selenium", hint: "Java framework" },
  { name: "playwright_code", label: "Playwright", hint: "TS framework" },
  { name: "vwo_testcases", label: "Test Cases", hint: "VWO CSV" },
  { name: "vwo_docs", label: "PRDs / Docs", hint: "PDFs" },
  { name: "vwo_bugs", label: "JIRA Bugs", hint: "MD exports" },
];

type Props = {
  forced: string[] | null;
  onChange: (forced: string[] | null) => void;
};

export default function SourceFilter({ forced, onChange }: Props) {
  const [open, setOpen] = useState(true);
  const isForced = forced !== null;
  const selected = new Set(forced ?? []);

  const toggle = (name: string) => {
    const next = new Set(selected);
    if (next.has(name)) next.delete(name);
    else next.add(name);
    onChange(next.size === 0 ? null : Array.from(next));
  };

  return (
    <div className="border border-gray-200 rounded-lg bg-white">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 text-sm font-semibold text-ink"
      >
        <span>Source filter</span>
        <span className="text-ink-muted text-[11px]">{open ? "hide" : "show"}</span>
      </button>
      {open && (
        <div className="px-3 pb-3 space-y-2">
          <div className="text-[11px] text-ink-muted">
            {isForced ? "Searching only the selected collections." : "Auto: router decides."}
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ALL.map((c) => {
              const on = selected.has(c.name);
              return (
                <button
                  key={c.name}
                  onClick={() => toggle(c.name)}
                  className={`text-[12px] px-2 py-1 rounded-md border transition ${
                    on
                      ? "bg-accent-soft text-accent-strong border-accent/40 font-semibold"
                      : "bg-surface-card text-ink-soft border-gray-200 hover:border-accent/40"
                  }`}
                  title={c.hint}
                >
                  {c.label}
                </button>
              );
            })}
          </div>
          {isForced && (
            <button
              onClick={() => onChange(null)}
              className="text-[11px] text-accent-strong underline"
            >
              clear (back to auto)
            </button>
          )}
        </div>
      )}
    </div>
  );
}
