/** The official Solvix wordmark and icon.
 *
 * Both come from `public/branding` and `public/solvix-icon-assets` as supplied
 * — never redrawn in markup, never recoloured, never re-proportioned. Sizing
 * is by height with `width: auto`, so the lockup scales without distortion at
 * any size.
 *
 * One thing the asset dictates: the "Solv" of the wordmark is pure white, so
 * it is legible on a dark surface and invisible on a light one. Rather than
 * recolour it, the light theme sets the mark on a dark plate — the standard
 * way to place a single-tone lockup on a background it was not drawn for. A
 * light-background export would be better; until there is one, this keeps the
 * artwork exactly as designed.
 */

const WORDMARK = "/branding/Solvix-wordmark-no-gap.svg";
const ICON = "/solvix-icon-assets/solvix-icon-256.png";

export function Logo({
  height = 28,
  className = "",
}: {
  height?: number;
  className?: string;
}) {
  return (
    <span className={`logo ${className}`.trim()}>
      <img
        src={WORDMARK}
        alt="Solvix"
        height={height}
        style={{ height }}
        // Loaded eagerly and given its ratio up front: this is the first thing
        // painted on the page, and a logo that arrives late shifts everything
        // under it.
        width={Math.round(height * (1700 / 560))}
        decoding="async"
      />
    </span>
  );
}

/** Icon only, for anywhere the wordmark will not fit. */
export function LogoIcon({
  size = 24,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <img
      className={`logo-icon ${className}`.trim()}
      src={ICON}
      alt="Solvix"
      width={size}
      height={size}
      decoding="async"
    />
  );
}
