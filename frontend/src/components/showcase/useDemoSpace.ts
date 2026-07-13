import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { apiGet, apiPost, ApiError } from "@/lib/api";
import type { CreateSpaceResponse } from "@/lib/types";

const SPACE_STORAGE_KEY = "wm_demo_space_id";
// Sentinel requestedRef key for "no candidate id at all" — distinct from any
// real space id so it can share the same dedupe guard below.
const NO_CANDIDATE = "__none__";

export interface DemoSpace {
  spaceId: string | null;
  /** True once a space id is known (existing, verified, or just created). */
  ready: boolean;
  /** True while the initial space is being provisioned/verified. */
  creating: boolean;
}

function readCandidateSpaceId(searchParams: URLSearchParams): string | null {
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
 * A candidate id from the URL or localStorage is never trusted blind: the
 * backend space store is in-memory/single-instance, so an id surviving a
 * redeploy/restart is dead, and every consumer (chat provisioning, leads,
 * sockets) 404s identically against it. This hook confirms the candidate
 * against the backend first — via the same `GET /spaces/{id}/leads` probe
 * `routes/present/index.tsx` proved out — and self-heals by clearing the
 * stale localStorage entry and minting a fresh space on a 404, so no
 * consumer (including a Command Center persona link) is ever handed a dead
 * `?space=`.
 *
 * Uses `apiPost`/`apiGet` directly instead of TanStack query hooks: this
 * fires from a mount effect, and StrictMode's simulated unmount/remount
 * silently drops TanStack v5 mutation updates issued in that window
 * (verified live — the POST returned 200 but the observer stayed "pending"
 * forever). Plain promises into local state have no such subscription
 * dependency.
 */
export function useDemoSpace(): DemoSpace {
  const [searchParams, setSearchParams] = useSearchParams();
  const [candidateId] = useState<string | null>(() => readCandidateSpaceId(searchParams));
  const [spaceId, setSpaceId] = useState<string | null>(null);
  // Keyed by candidate id (or NO_CANDIDATE) rather than a plain boolean so a
  // 404-triggered re-mint of a *different* id doesn't get skipped by a guard
  // still latched to the original candidate.
  const requestedRef = useRef<string | null>(null);

  useEffect(() => {
    if (spaceId) return;
    const key = candidateId ?? NO_CANDIDATE;
    if (requestedRef.current === key) return;
    requestedRef.current = key;
    // No cancellation flag on purpose: StrictMode runs cleanup between its
    // two mount passes while requestedRef skips the second pass, so a flag
    // would permanently swallow the only response. setState after a real
    // unmount is a safe no-op in React 18+.

    if (!candidateId) {
      apiPost<CreateSpaceResponse>("/spaces")
        .then((res) => setSpaceId(res.space_id))
        .catch(() => {
          // Allow a retry on remount rather than wedging in a dead state.
          requestedRef.current = null;
        });
      return;
    }

    apiGet(`/spaces/${candidateId}/leads`)
      .then(() => setSpaceId(candidateId))
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 404) {
          window.localStorage.removeItem(SPACE_STORAGE_KEY);
          apiPost<CreateSpaceResponse>("/spaces")
            .then((res) => setSpaceId(res.space_id))
            .catch(() => {
              requestedRef.current = null;
            });
        } else {
          requestedRef.current = null;
        }
      });
  }, [spaceId, candidateId]);

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
