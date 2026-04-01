import { useCallback, useSyncExternalStore } from "react";
import {
  getBookmarkIds,
  isBookmarked,
  toggleBookmark,
  libraryStorageEvents,
} from "@/lib/userLibraryStorage";

function subscribeBookmarkChanges(cb: () => void) {
  const handler = () => cb();
  window.addEventListener(libraryStorageEvents.bookmarks, handler);
  window.addEventListener("storage", handler);
  return () => {
    window.removeEventListener(libraryStorageEvents.bookmarks, handler);
    window.removeEventListener("storage", handler);
  };
}

export function useBookmark(paperId: string | undefined) {
  const bookmarked = useSyncExternalStore(
    subscribeBookmarkChanges,
    () => (paperId ? isBookmarked(paperId) : false),
    () => false
  );

  const toggle = useCallback(() => {
    if (!paperId) return;
    toggleBookmark(paperId);
  }, [paperId]);

  return { bookmarked, toggle };
}

export function useBookmarkCount() {
  return useSyncExternalStore(
    subscribeBookmarkChanges,
    () => getBookmarkIds().length,
    () => 0
  );
}
