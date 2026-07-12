import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiPost } from "@/lib/api";
import type { CreateSpaceResponse } from "@/lib/types";

const SPACE_STORAGE_KEY = "wm_demo_space_id";

export interface DemoSpace {
  spaceId: string | null;
  /** True once a space id is known (existing or just created). */
  ready: boolean;
  /** True while the initial space is being provisioned. */
  creating: boolean;
}

function readInitialSpaceId(searchParams: URLSearchParams): string | null {
  const fromUrl = searchParams.get("space");
  if (fromUrl) return fromUrl;
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(SPACE_STORAGE_KEY);
}

/**
 * Shared across the Command Center, Omni-channel, and Presenter routes so
 * all three land on the same demo space without every route re-deriving
 * its own creation/persistence logic. Resolution order: `?space=` in the
 * URL, then the last space this browser created, then a fresh
 * `POST /api/spaces`. Once resolved, the id is mirrored into both
 * localStorage and the URL so any link a screen builds (including an
 * iframe `src`) carries `?space=` forward.
 *
 * Uses `apiPost` directly instead of `useCreateSpace()`: this fires from a
 * mount effect, and StrictMode's simulated unmount/remount silently drops
 * TanStack v5 mutation updates issued in that window (verified live — the
 * POST returned 200 but the observer stayed "pending" forever). A plain
 * promise into local state has no such subscription dependency.
 */
export function useDemoSpace(): DemoSpace {
  const [searchParams, setSearchParams] = useSearchParams();
  const [spaceId, setSpaceId] = useState<string | null>(() => readInitialSpaceId(searchParams));
  const requestedRef = useRef(false);

  useEffect(() => {
    if (spaceId || requestedRef.current) return;
    requestedRef.current = true;
    // No cancellation flag on purpose: StrictMode runs cleanup between its
    // two mount passes while requestedRef skips the second pass, so a flag
    // would permanently swallow the only response. setState after a real
    // unmount is a safe no-op in React 18+.
    apiPost<CreateSpaceResponse>("/spaces")
      .then((res) => setSpaceId(res.space_id))
      .catch(() => {
        // Allow a retry on remount rather than wedging in a dead state.
        requestedRef.current = false;
      });
  }, [spaceId]);

  useEffect(() => {
    if (!spaceId) return;
    window.localStorage.setItem(SPACE_STORAGE_KEY, spaceId);
    if (searchParams.get("space") !== spaceId) {
      const next = new URLSearchParams(searchParams);
      next.set("space", spaceId);
      setSearchParams(next, { replace: true });
    }
    // Sync only when the resolved id changes — searchParams/setSearchParams
    // change identity on every navigation and would loop this effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spaceId]);

  return { spaceId, ready: Boolean(spaceId), creating: !spaceId };
}
