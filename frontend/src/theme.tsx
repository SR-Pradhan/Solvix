import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

export type Theme = "dark" | "light";

const STORAGE_KEY = "solvix-theme";

function stored(): Theme | null {
  const value = localStorage.getItem(STORAGE_KEY);
  return value === "dark" || value === "light" ? value : null;
}

/** A saved choice wins; otherwise follow the operating system. */
function initial(): Theme {
  return (
    stored() ??
    (window.matchMedia("(prefers-color-scheme: light)").matches
      ? "light"
      : "dark")
  );
}

/**
 * Written to the document straight away rather than from an effect.
 * `useThemeTokens` reads resolved colours during render, so the attribute has
 * to be in place before React re-renders, not after.
 */
function apply(theme: Theme) {
  document.documentElement.dataset.theme = theme;
}

apply(initial());

const ThemeContext = createContext<{ theme: Theme; toggle: () => void } | null>(
  null,
);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(initial);

  const toggle = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem(STORAGE_KEY, next);
      apply(next);
      return next;
    });
  }, []);

  const value = useMemo(() => ({ theme, toggle }), [theme, toggle]);

  return (
    <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
  );
}

export function useTheme() {
  const value = useContext(ThemeContext);
  if (!value) throw new Error("useTheme used outside ThemeProvider");
  return value;
}

const CHART_TOKENS = [
  "accent",
  "ok",
  "warn",
  "danger",
  "violet",
  "muted",
  // Axis ticks and the tooltip edge: charts need the quieter greys too, and a
  // token missing here silently resolves to an empty string.
  "faint",
  "border",
  "border-strong",
  "surface",
  "surface-2",
  "text",
] as const;

export type ChartTokens = Record<(typeof CHART_TOKENS)[number], string>;

/**
 * Resolved hex values for the current theme.
 *
 * Charts draw into SVG, where `var(--ok)` is not honoured in presentation
 * attributes, so the values have to be read out of the cascade in JavaScript
 * and passed to Recharts as plain strings.
 */
export function useThemeTokens(): ChartTokens {
  const { theme } = useTheme();

  return useMemo(() => {
    const style = getComputedStyle(document.documentElement);
    const entries = CHART_TOKENS.map((token) => [
      token,
      style.getPropertyValue(`--${token}`).trim(),
    ]);
    return Object.fromEntries(entries) as ChartTokens;
    // Recomputed on every theme change; the values are static within a theme.
  }, [theme]);
}
