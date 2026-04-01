import { useSyncExternalStore } from "react";
import {
  countHistoryThisWeek,
  getBookmarkIds,
  getQuestionLog,
  subscribeLibraryChanges,
} from "@/lib/userLibraryStorage";

export function useDashboardStats() {
  return useSyncExternalStore(
    subscribeLibraryChanges,
    () => ({
      bookmarks: getBookmarkIds().length,
      readThisWeek: countHistoryThisWeek(),
      questions: getQuestionLog().length,
    }),
    () => ({
      bookmarks: 0,
      readThisWeek: 0,
      questions: 0,
    })
  );
}
