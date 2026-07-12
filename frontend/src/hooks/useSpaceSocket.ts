import { useCallback, useEffect, useRef, useState } from "react";
import type { SpaceSocketEvent, SpaceSocketEventMap, SpaceSocketEventType } from "@/lib/types";

type Handler<T extends SpaceSocketEventType> = (payload: SpaceSocketEventMap[T]) => void;
type Unsubscribe = () => void;

type Listeners = {
  [K in SpaceSocketEventType]?: Set<Handler<K>>;
};

export interface UseSpaceSocketResult {
  connected: boolean;
  /** Registers a handler for one event type; returns an unsubscribe function. */
  subscribe: <T extends SpaceSocketEventType>(type: T, handler: Handler<T>) => Unsubscribe;
}

const BASE_BACKOFF_MS = 500;
const MAX_BACKOFF_MS = 15_000;

/**
 * Subscribes to `/ws/{spaceId}` (typed event union) with automatic
 * exponential-backoff reconnect. Connects on mount / whenever `spaceId`
 * changes, and tears the socket + any pending reconnect timer down on
 * unmount so no surface can leak a stale connection.
 */
export function useSpaceSocket(spaceId: string | null | undefined): UseSpaceSocketResult {
  const [connected, setConnected] = useState(false);
  const listenersRef = useRef<Listeners>({});
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<number | null>(null);
  const attemptRef = useRef(0);
  const unmountedRef = useRef(false);

  const subscribe = useCallback<UseSpaceSocketResult["subscribe"]>((type, handler) => {
    // TS can't correlate a generic `T` with the matching branch of the
    // `Listeners` mapped type through a plain indexed assignment — the
    // invariant (a set at key `type` only ever holds `Handler<type>`s) is
    // guaranteed by this function being the sole writer, so the cast here
    // is safe and kept local to this one call site.
    const listeners = listenersRef.current as Record<
      SpaceSocketEventType,
      Set<Handler<SpaceSocketEventType>> | undefined
    >;
    let set = listeners[type];
    if (!set) {
      set = new Set();
      listeners[type] = set;
    }
    set.add(handler as Handler<SpaceSocketEventType>);
    return () => {
      set?.delete(handler as Handler<SpaceSocketEventType>);
    };
  }, []);

  useEffect(() => {
    if (!spaceId) return;
    unmountedRef.current = false;
    attemptRef.current = 0;

    function scheduleReconnect() {
      if (unmountedRef.current) return;
      const attempt = attemptRef.current + 1;
      attemptRef.current = attempt;
      const backoff = Math.min(BASE_BACKOFF_MS * 2 ** (attempt - 1), MAX_BACKOFF_MS);
      reconnectTimerRef.current = window.setTimeout(connect, backoff);
    }

    function connect() {
      if (unmountedRef.current) return;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const socket = new WebSocket(`${protocol}//${window.location.host}/ws/${spaceId}`);
      socketRef.current = socket;

      socket.onopen = () => {
        attemptRef.current = 0;
        setConnected(true);
      };

      socket.onmessage = (event) => {
        let parsed: SpaceSocketEvent;
        try {
          parsed = JSON.parse(event.data) as SpaceSocketEvent;
        } catch {
          return;
        }
        const set = listenersRef.current[parsed.type];
        set?.forEach((handler) => (handler as (payload: unknown) => void)(parsed.payload));
      };

      socket.onclose = () => {
        setConnected(false);
        socketRef.current = null;
        scheduleReconnect();
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      unmountedRef.current = true;
      if (reconnectTimerRef.current !== null) {
        window.clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      socketRef.current?.close();
      socketRef.current = null;
      setConnected(false);
    };
  }, [spaceId]);

  return { connected, subscribe };
}
