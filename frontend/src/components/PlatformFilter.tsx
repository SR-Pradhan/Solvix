import type { Platform } from "../api/types";

const LABELS: Record<Platform, string> = {
  codeforces: "Codeforces",
  leetcode: "LeetCode",
};

export function PlatformFilter({
  available,
  value,
  onChange,
}: {
  available: Platform[];
  value: Platform | null;
  onChange: (next: Platform | null) => void;
}) {
  // With one platform connected there is nothing to filter between.
  if (available.length < 2) return null;

  return (
    <div className="filter">
      <button
        className={`chip-btn${value === null ? " on" : ""}`}
        onClick={() => onChange(null)}
      >
        All
      </button>
      {available.map((p) => (
        <button
          key={p}
          className={`chip-btn${value === p ? " on" : ""}`}
          onClick={() => onChange(p)}
        >
          {LABELS[p]}
        </button>
      ))}
    </div>
  );
}
