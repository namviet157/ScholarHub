import katex from "katex";
import "katex/dist/katex.min.css";
import { cn } from "@/lib/utils";
import type { ReactNode } from "react";

function renderTex(tex: string, displayMode: boolean): string {
  try {
    return katex.renderToString(tex.trim(), {
      displayMode,
      throwOnError: false,
      strict: "ignore",
    });
  } catch {
    return `<span class="text-destructive text-xs">[invalid math]</span>`;
  }
}

function splitInline(text: string) {
  const re = /\$((?:\\.|[^$])+?)\$/g;
  const out: ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  let key = 0;
  const s = text;
  while ((m = re.exec(s)) !== null) {
    if (m.index > last) {
      out.push(
        <span key={`t-${key++}`} className="whitespace-pre-wrap">
          {s.slice(last, m.index)}
        </span>
      );
    }
    out.push(
      <span
        key={`m-${key++}`}
        className="inline-block align-middle max-w-full overflow-x-auto"
        dangerouslySetInnerHTML={{ __html: renderTex(m[1]!, false) }}
      />
    );
    last = m.index + m[0].length;
  }
  if (last < s.length) {
    out.push(
      <span key={`t-${key++}`} className="whitespace-pre-wrap">
        {s.slice(last)}
      </span>
    );
  }
  return out.length > 0 ? out : [<span key="0" className="whitespace-pre-wrap">{text}</span>];
}

/**
 * Renders mixed text with KaTeX for $...$, $$...$$, \\(...\\), \\[...\\].
 * Raw LaTeX outside math (e.g. \\section, \\cite) stays as plain text.
 */
export function LatexContent({ text, className }: { text: string; className?: string }) {
  const normalized = text
    .replace(/\\\[([\s\S]*?)\\\]/g, (_, inner) => `$$${String(inner).trim()}$$`)
    .replace(/\\\(([\s\S]*?)\\\)/g, (_, inner) => `$${String(inner).trim()}$`);

  const blocks = normalized.split(/\$\$/g);

  return (
    <div className={cn("leading-relaxed break-words", className)}>
      {blocks.map((block, idx) => (
        <div key={idx}>
          {idx % 2 === 1 ? (
            <div
              className="my-3 overflow-x-auto max-w-full [&_.katex]:text-base"
              dangerouslySetInnerHTML={{ __html: renderTex(block, true) }}
            />
          ) : (
            <div>{splitInline(block)}</div>
          )}
        </div>
      ))}
    </div>
  );
}
