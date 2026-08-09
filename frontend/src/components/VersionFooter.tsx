import { useEffect, useState } from "react";

import { api } from "../api/client";

/** Names the running build, so the page and the GitHub tag can be compared.
 *
 * The version comes from the API rather than the frontend bundle on purpose:
 * the two deploy separately, and the number worth showing is the one belonging
 * to the service actually answering.
 */
export function VersionFooter() {
  const [version, setVersion] = useState<string | null>(null);
  const [reachable, setReachable] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then((h) => !cancelled && setVersion(h.version))
      .catch(() => !cancelled && setReachable(false));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <footer className="version-footer muted small">
      <span>Solvix{version ? ` v${version}` : ""}</span>
      <span aria-hidden="true">·</span>
      <a
        href="https://github.com/SR-Pradhan/Solvix"
        target="_blank"
        rel="noreferrer"
      >
        Source
      </a>
      {!reachable && (
        <>
          <span aria-hidden="true">·</span>
          {/* The free API sleeps when idle, so an unreachable backend is
              usually a cold start rather than an outage. */}
          <span>API waking up…</span>
        </>
      )}
    </footer>
  );
}
