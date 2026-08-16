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

import type { CSSProperties } from "react";

const WORDMARK = "/branding/Solvix-wordmark-no-gap.svg";
const ICON = "/solvix-icon-assets/solvix-icon-128.png";

export function Logo({
  height,
  className = "",
}: {
  /** Omit to let CSS decide — an inline value would win over any stylesheet
   *  rule, which is exactly what stopped the boot screen's `clamp()` from
   *  ever applying. */
  height?: number;
  className?: string;
}) {
  return (
    // The height travels as a custom property rather than an inline style, so
    // a media query can shrink the lockup without fighting a specificity war
    // with the element's own attribute.
    <span
      className={`logo ${className}`.trim()}
      style={
        height === undefined
          ? undefined
          : ({ "--logo-h": `${height}px` } as CSSProperties)
      }
    >
      <img
        src={WORDMARK}
        alt="Solvix"
        // The intrinsic size is declared so the box is reserved before the
        // image arrives: this is the first thing painted, and a logo that
        // lands late shifts everything under it.
        width={1700}
        height={560}
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
