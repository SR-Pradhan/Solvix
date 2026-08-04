/**
 * The affordance for opening a row's problem list.
 *
 * The topic name is clickable too, but a bare word does not look like a
 * control — this gives every row a visible, consistent handle.
 */
export function ProblemsToggle({
  open,
  onClick,
  label,
}: {
  open: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      className={`problems-toggle${open ? " open" : ""}`}
      onClick={onClick}
      aria-expanded={open}
      aria-label={`${open ? "Hide" : "Show"} problems for ${label}`}
      title={open ? "Hide problems" : "Show problems"}
    >
      <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
        <path
          d="M6 3.5 10.5 8 6 12.5"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    </button>
  );
}
