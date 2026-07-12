import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";
import type { AvatarState } from "@/lib/types";

export type { AvatarState };

export interface AvatarProps {
  state?: AvatarState;
  /** Diameter in px. */
  size?: number;
  className?: string;
  "aria-label"?: string;
}

// Timing is derived from the token scale in styles/tokens.css
// (--motion-micro/-state/-screen = 150/220/350ms) rather than invented
// values — ambient loops below chain these into full breathe/pulse/bounce
// cycles instead of using them as one-shot transition durations.
const MICRO = 0.15;
const STATE = 0.22;
const SCREEN = 0.35;
const EASE_OUT: [number, number, number, number] = [0.22, 1, 0.36, 1];
const EASE_IN_OUT: [number, number, number, number] = [0.65, 0, 0.35, 1];

function loop(duration: number, delay = 0, reduce = false) {
  if (reduce) return { duration: 0.01 };
  return { duration, repeat: Infinity, ease: EASE_IN_OUT, delay };
}

/**
 * The WealthMitra companion — a friendly abstract orb mascot (structural
 * teal body, brand-orange accent badge), never an emoji or stock
 * illustration. Purely CSS/SVG + Framer Motion, state-driven.
 */
export function Avatar({
  state = "idle",
  size = 96,
  className,
  "aria-label": ariaLabel,
}: AvatarProps) {
  const reduceMotion = Boolean(useReducedMotion());

  const bodyAnimate =
    state === "idle"
      ? { y: [0, -2, 0], scale: [1, 1.015, 1] }
      : state === "celebrating"
        ? { y: [0, -7, 0] }
        : { y: 0, scale: 1 };

  const bodyTransition =
    state === "idle"
      ? loop(SCREEN * 2, 0, reduceMotion)
      : state === "celebrating"
        ? reduceMotion
          ? { duration: 0.01 }
          : { duration: STATE * 2, repeat: 3, ease: EASE_OUT }
        : { duration: STATE, ease: EASE_OUT };

  return (
    <div
      role="img"
      aria-label={ariaLabel ?? `WealthMitra avatar, ${state}`}
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: size, height: size }}
    >
      {state === "listening" && (
        <motion.span
          className="absolute inset-0 rounded-full bg-structural-400"
          animate={reduceMotion ? { opacity: 0.25 } : { scale: [1, 1.16, 1], opacity: [0.32, 0, 0.32] }}
          transition={loop(SCREEN * 2, 0, reduceMotion)}
        />
      )}

      <motion.svg
        viewBox="0 0 96 96"
        width={size}
        height={size}
        className="relative"
        animate={bodyAnimate}
        transition={bodyTransition}
      >
        <circle cx={48} cy={48} r={44} className="fill-structural-500" />
        <ellipse cx={36} cy={30} rx={16} ry={10} className="fill-structural-300" opacity={0.35} />

        {/* Brand-orange accent badge, set low so it reads as a collar pin
            rather than a mole beside the mouth/expression area. */}
        <circle cx={73} cy={76} r={7} className="fill-brand-500" />
        <circle cx={73} cy={76} r={2.4} className="fill-brand-100" />

        {/* Eyes */}
        {state === "celebrating" ? (
          <g className="stroke-neutral-900" strokeWidth={3.5} strokeLinecap="round" fill="none">
            <path d="M28 42 Q34 34 40 42" />
            <path d="M56 42 Q62 34 68 42" />
          </g>
        ) : state === "concerned" ? (
          <>
            <g className="stroke-neutral-700" strokeWidth={3} strokeLinecap="round">
              <path d="M27 33 L41 37" />
              <path d="M69 33 L55 37" />
            </g>
            <ellipse cx={34} cy={44} rx={4.5} ry={5.5} className="fill-neutral-900" />
            <ellipse cx={62} cy={44} rx={4.5} ry={5.5} className="fill-neutral-900" />
          </>
        ) : (
          <>
            <motion.ellipse
              cx={34}
              cy={42}
              rx={4.5}
              ry={6}
              className="fill-neutral-900"
              animate={state === "listening" ? { ry: [6, 7, 6] } : { ry: 6 }}
              transition={loop(SCREEN * 3, 0, reduceMotion)}
            />
            <motion.ellipse
              cx={62}
              cy={42}
              rx={4.5}
              ry={6}
              className="fill-neutral-900"
              animate={state === "listening" ? { ry: [6, 7, 6] } : { ry: 6 }}
              transition={loop(SCREEN * 3, 0.1, reduceMotion)}
            />
          </>
        )}

        {/* Mouth / expression area */}
        <AnimatePresence mode="wait">
          {state === "speaking" ? (
            <motion.g
              key="speaking"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: MICRO }}
            >
              {[0, 1, 2, 3].map((i) => (
                <motion.rect
                  key={i}
                  x={38 + i * 6}
                  y={60}
                  width={3}
                  height={8}
                  rx={1.5}
                  className="fill-neutral-900"
                  style={{ transformOrigin: "48px 64px" }}
                  animate={{ scaleY: [0.4, 1, 0.4] }}
                  transition={loop(STATE * 2, i * 0.08, reduceMotion)}
                />
              ))}
            </motion.g>
          ) : state === "thinking" ? (
            <motion.g
              key="thinking"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: MICRO }}
            >
              {[0, 1, 2].map((i) => (
                <motion.circle
                  key={i}
                  cx={40 + i * 8}
                  cy={64}
                  r={2.6}
                  className="fill-neutral-900"
                  animate={{ opacity: [0.25, 1, 0.25], y: [0, -3, 0] }}
                  transition={loop(SCREEN * 2, i * STATE, reduceMotion)}
                />
              ))}
            </motion.g>
          ) : state === "celebrating" ? (
            <motion.path
              key="celebrating"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: MICRO }}
              d="M32 60 Q48 76 64 60"
              className="stroke-neutral-900"
              strokeWidth={3.5}
              strokeLinecap="round"
              fill="none"
            />
          ) : state === "concerned" ? (
            <motion.path
              key="concerned"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: MICRO }}
              d="M36 68 Q48 58 60 68"
              className="stroke-neutral-700"
              strokeWidth={3}
              strokeLinecap="round"
              fill="none"
            />
          ) : state === "listening" ? (
            <motion.circle
              key="listening"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: MICRO }}
              cx={48}
              cy={64}
              r={3}
              className="fill-neutral-900"
            />
          ) : (
            <motion.rect
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: MICRO }}
              x={40}
              y={62}
              width={16}
              height={3}
              rx={1.5}
              className="fill-neutral-900"
            />
          )}
        </AnimatePresence>
      </motion.svg>
    </div>
  );
}
