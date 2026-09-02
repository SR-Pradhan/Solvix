import { AnimatePresence, motion } from "framer-motion";
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

type Kind = "ok" | "error" | "info";
type Toast = { id: number; kind: Kind; text: string };

const ToastContext = createContext<(text: string, kind?: Kind) => void>(() => {});

/** One channel for feedback.
 *
 * Before this, a sync result or an error appeared as a line of text wherever
 * the component that produced it happened to be — which, after a scroll, was
 * nowhere you were looking. Toasts put every outcome in the same corner, and
 * `aria-live` reads them to a screen reader without stealing focus.
 */
export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(1);

  const push = useCallback((text: string, kind: Kind = "info") => {
    const id = next.current++;
    setToasts((all) => [...all, { id, kind, text }]);
    // Errors stay longer: they are the ones you need to read.
    setTimeout(
      () => setToasts((all) => all.filter((t) => t.id !== id)),
      kind === "error" ? 7000 : 4000,
    );
  }, []);

  const value = useMemo(() => push, [push]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="toasts" aria-live="polite" aria-atomic="false">
        <AnimatePresence initial={false}>
          {toasts.map((t) => (
            <motion.div
              key={t.id}
              className={`toast toast-${t.kind}`}
              role={t.kind === "error" ? "alert" : "status"}
              initial={{ opacity: 0, y: 12, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.98 }}
              transition={{ duration: 0.22 }}
            >
              {t.text}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  return useContext(ToastContext);
}
