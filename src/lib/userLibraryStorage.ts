const BOOKMARKS = "scholarhub:bookmarks";
const HISTORY = "scholarhub:history";
const QUESTIONS = "scholarhub:questions";

/** Works when `crypto.randomUUID` is missing (some non-secure contexts / older browsers). */
function newLocalId(): string {
  const c = globalThis.crypto;
  if (c && typeof c.randomUUID === "function") {
    return c.randomUUID();
  }
  if (c && typeof c.getRandomValues === "function") {
    const buf = new Uint8Array(16);
    c.getRandomValues(buf);
    buf[6] = (buf[6]! & 0x0f) | 0x40;
    buf[8] = (buf[8]! & 0x3f) | 0x80;
    const hex = [...buf].map((b) => b.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `q-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

export const libraryStorageEvents = {
  bookmarks: "scholarhub:bookmarks-changed",
  history: "scholarhub:history-changed",
  questions: "scholarhub:questions-changed",
} as const;

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value));
}

export function getBookmarkIds(): string[] {
  return readJson<string[]>(BOOKMARKS, []);
}

export function isBookmarked(paperId: string): boolean {
  return getBookmarkIds().includes(paperId);
}

/** @returns new bookmarked state */
export function toggleBookmark(paperId: string): boolean {
  const cur = getBookmarkIds();
  const next = cur.includes(paperId) ? cur.filter((id) => id !== paperId) : [...cur, paperId];
  writeJson(BOOKMARKS, next);
  window.dispatchEvent(new Event(libraryStorageEvents.bookmarks));
  return next.includes(paperId);
}

export type HistoryEntry = {
  paperId: string;
  title: string;
  viewedAt: string;
};

export function recordPaperView(paperId: string, title: string): void {
  const prev = readJson<HistoryEntry[]>(HISTORY, []);
  const filtered = prev.filter((e) => e.paperId !== paperId);
  const next: HistoryEntry[] = [
    { paperId, title, viewedAt: new Date().toISOString() },
    ...filtered,
  ].slice(0, 200);
  writeJson(HISTORY, next);
  window.dispatchEvent(new Event(libraryStorageEvents.history));
}

export function getReadingHistory(): HistoryEntry[] {
  return readJson<HistoryEntry[]>(HISTORY, []);
}

export type QuestionLogEntry = {
  id: string;
  question: string;
  answer: string;
  at: string;
  paperIds?: string[];
};

export function appendQuestionLog(entry: Omit<QuestionLogEntry, "id" | "at">): void {
  const prev = readJson<QuestionLogEntry[]>(QUESTIONS, []);
  const row: QuestionLogEntry = {
    id: newLocalId(),
    at: new Date().toISOString(),
    ...entry,
  };
  writeJson(QUESTIONS, [row, ...prev].slice(0, 100));
  window.dispatchEvent(new Event(libraryStorageEvents.questions));
}

export function getQuestionLog(): QuestionLogEntry[] {
  return readJson<QuestionLogEntry[]>(QUESTIONS, []);
}

/** Distinct papers viewed in the last 7 days */
export function countHistoryThisWeek(): number {
  const h = getReadingHistory();
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  const ids = new Set(
    h.filter((e) => new Date(e.viewedAt).getTime() >= weekAgo).map((e) => e.paperId)
  );
  return ids.size;
}

export function subscribeLibraryChanges(cb: () => void) {
  const handler = () => cb();
  Object.values(libraryStorageEvents).forEach((ev) =>
    window.addEventListener(ev, handler)
  );
  window.addEventListener("storage", handler);
  return () => {
    Object.values(libraryStorageEvents).forEach((ev) =>
      window.removeEventListener(ev, handler)
    );
    window.removeEventListener("storage", handler);
  };
}

export function formatRelativeTime(iso: string): string {
  const d = new Date(iso);
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return d.toLocaleDateString();
}
