import { useCallback, useEffect, useRef, useState } from "react";

// Minimum time (ms) each status line stays visible before the next one replaces
// it, so a fast graph doesn't flash several lines by in a blink.
const MIN_DISPLAY_MS = 600;

/**
 * Paces a stream of status strings so each is shown for at least `minMs`.
 *
 * Incoming statuses queue up and are revealed one at a time, holding each for
 * the minimum before advancing to the next. The opener shows immediately (no
 * prior line to hold). `reset` clears the queue, any pending timer, and the
 * displayed line — call it when the answer starts and when the turn ends.
 */
export function usePacedStatus(minMs: number = MIN_DISPLAY_MS) {
  const [status, setStatus] = useState("");
  const queueRef = useRef<string[]>([]);
  const shownAtRef = useRef(0); // 0 = nothing shown yet → show the next one now
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  // Reveal the next queued status if the current one has had its minimum time;
  // otherwise re-arm a timer for the remaining hold.
  const advance = useCallback(() => {
    timerRef.current = null;
    if (queueRef.current.length === 0) return;

    const elapsed = Date.now() - shownAtRef.current;
    const wait = shownAtRef.current === 0 ? 0 : Math.max(0, minMs - elapsed);
    if (wait > 0) {
      timerRef.current = setTimeout(advance, wait);
      return;
    }

    setStatus(queueRef.current.shift() as string);
    shownAtRef.current = Date.now();
    if (queueRef.current.length > 0) {
      timerRef.current = setTimeout(advance, minMs);
    }
  }, [minMs]);

  const push = useCallback(
    (next: string) => {
      queueRef.current.push(next);
      if (!timerRef.current) advance(); // no timer pending → try to show now
    },
    [advance],
  );

  const reset = useCallback(() => {
    clearTimer();
    queueRef.current = [];
    shownAtRef.current = 0;
    setStatus("");
  }, [clearTimer]);

  useEffect(() => () => clearTimer(), [clearTimer]); // clear on unmount

  return { status, push, reset };
}
