import { motion, useReducedMotion } from "framer-motion";
import type { ReactNode } from "react";

/** A card arriving.
 *
 * Fade and a short rise, staggered by position so a screen of cards reads as
 * one settling gesture rather than twelve things popping in. Once only — on a
 * data refresh the content changes in place, because animating cards that
 * were already there makes the page feel like it reloaded.
 *
 * Under "reduce motion" the wrapper is inert: the content simply appears.
 */
export function Reveal({
  children,
  index = 0,
  className,
}: {
  children: ReactNode;
  index?: number;
  className?: string;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.32, delay: Math.min(index, 8) * 0.05, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
