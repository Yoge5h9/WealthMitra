import { motion, useReducedMotion } from "framer-motion";

const EASE_IN_OUT: [number, number, number, number] = [0.65, 0, 0.35, 1];
const STATE = 0.22;

/** Three-dot typing indicator shown before the first token of a turn
 * arrives — never a bare spinner; the loading state is shaped like the
 * real content, here a not-yet-arrived text bubble. */
export function TypingIndicator() {
  const reduceMotion = Boolean(useReducedMotion());
  return (
    <div
      role="status"
      aria-label="WealthMitra is typing"
      className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 bg-neutral-0 px-4 py-3"
    >
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="size-2 rounded-full bg-neutral-400"
          animate={reduceMotion ? { opacity: 0.6 } : { opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={
            reduceMotion
              ? { duration: 0.01 }
              : { duration: STATE * 3, repeat: Infinity, ease: EASE_IN_OUT, delay: i * STATE }
          }
        />
      ))}
    </div>
  );
}
