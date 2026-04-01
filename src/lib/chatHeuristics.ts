import type { Paper } from "@/types/scholar";

function tokenize(s: string): string[] {
  return s
    .toLowerCase()
    .replace(/[^\w\s.]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 2);
}

function scorePaper(question: string, paper: Paper): number {
  const tokens = tokenize(question);
  if (tokens.length === 0) return 0;
  const blob = [paper.title, paper.abstract, paper.aiSummary, ...(paper.keywords ?? [])]
    .join(" ")
    .toLowerCase();
  let score = 0;
  for (const t of tokens) {
    if (blob.includes(t)) score += 1;
  }
  return score;
}

export function pickPapersForAnswer(question: string, papers: Paper[], max = 2): Paper[] {
  const scored = papers
    .map((p) => ({ p, s: scorePaper(question, p) }))
    .sort((a, b) => b.s - a.s);
  const withHits = scored.filter((x) => x.s > 0);
  const source = withHits.length ? withHits : scored;
  return source.slice(0, max).map((x) => x.p);
}

export function buildAnswerFromPapers(question: string, papers: Paper[]): {
  answer: string;
  citations: string[];
} {
  const picks = pickPapersForAnswer(question, papers, 2);
  if (picks.length === 0) {
    return {
      answer:
        "No papers are selected or your library is empty. Open **Explore** and load papers, then ask again.",
      citations: [],
    };
  }

  const primary = picks[0]!;
  const snippet =
    primary.abstract.length > 450
      ? `${primary.abstract.slice(0, 447).trim()}…`
      : primary.abstract || primary.aiSummary;

  const cite =
    primary.authors.length > 0
      ? `${primary.authors.slice(0, 2).join(", ")}${primary.authors.length > 2 ? " et al." : ""}, ${primary.year}`
      : primary.title;

  let body = `**${primary.title}**\n\n${snippet || "(No abstract in catalog.)"}`;

  if (picks.length > 1 && picks[1]) {
    const sec = picks[1];
    const bit =
      sec.abstract.length > 220 ? `${sec.abstract.slice(0, 217).trim()}…` : sec.abstract;
    body += `\n\n---\n\n**See also:** *${sec.title}* — ${bit}`;
  }

  body +=
    "\n\n*(Heuristic answer from abstracts in your catalog. Plug in an LLM API for deeper reasoning.)*";

  return {
    answer: body,
    citations: [cite, ...picks.slice(1).map((p) => p.title)],
  };
}
