import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = { text: string };

/**
 * Render markdown but turn [N] tokens (digits in brackets) into clickable
 * citation chips that scroll the matching source card into view.
 */
export default function MarkdownAnswer({ text }: Props) {
  const enriched = text.replace(/\[(\d+)\]/g, (_m, n) => `<cite>${n}</cite>`);
  return (
    <div className="markdown text-[15px] text-ink">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // @ts-expect-error: custom tag
          cite: ({ children }: any) => {
            const id = String(children).trim();
            return (
              <span
                className="cite-chip"
                onClick={() => {
                  const el = document.getElementById(`source-${id}`);
                  if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
                }}
                title={`Source ${id}`}
              >
                {id}
              </span>
            );
          },
        }}
      >
        {enriched}
      </ReactMarkdown>
    </div>
  );
}
