/** Placeholder shapes for content that has not arrived.
 *
 * The API sleeps when idle and takes up to a minute to wake, so a first visit
 * spends real time with nothing to show. The word "Loading…" makes that read
 * as a stall; blocks in the shape of the coming cards make it read as work in
 * progress, and they stop the page jumping when the content lands.
 *
 * Deliberately plain: no shimmer sweeping across the screen. An animation that
 * draws the eye competes with the content it is standing in for, and looks
 * worse the longer it runs — which here is precisely the case that matters.
 */
export function SkeletonCard({ lines = 3 }: { lines?: number }) {
  return (
    <section className="card skeleton" aria-hidden="true">
      <div className="skeleton-bar skeleton-title" />
      {Array.from({ length: lines }, (_, i) => (
        <div
          key={i}
          className="skeleton-bar"
          // Ragged rather than uniform: equal-length bars read as a table, and
          // the thing arriving is prose.
          style={{ width: `${92 - i * 14}%` }}
        />
      ))}
    </section>
  );
}

export function SkeletonStats() {
  return (
    <div className="stat-grid" aria-hidden="true">
      {Array.from({ length: 4 }, (_, i) => (
        <div key={i} className="card skeleton">
          <div className="skeleton-bar skeleton-label" />
          <div className="skeleton-bar skeleton-number" />
        </div>
      ))}
    </div>
  );
}

/** What the dashboard looks like while it is still arriving. */
export function DashboardSkeleton({ waking }: { waking: boolean }) {
  return (
    <>
      {/* Said out loud only once it is slow enough to need explaining. Telling
          everyone about the cold start on every load would advertise a
          weakness that most visits never notice. */}
      {waking && (
        <p className="muted small" role="status">
          Waking the server — this takes about a minute after a quiet spell.
        </p>
      )}
      <SkeletonStats />
      <SkeletonCard lines={4} />
      <SkeletonCard lines={3} />
    </>
  );
}
