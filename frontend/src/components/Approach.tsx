import { useState } from "react";

import { ApiError, api } from "../api/client";
import type { Approach as Data } from "../api/types";
import { useAuth } from "../auth";

/** Problems that were accepted without the technique they were teaching.
 *
 * Deliberately shows its working on every row. The claim — "you did not really
 * solve this one" — is the most contestable thing Solvix says, so the row names
 * what the problem was tagged with and what the code actually used, and links
 * to the problem so it can be argued with.
 */
export function Approach({ data, onSynced }: { data: Data; onSynced: (d: Data) => void }) {
  const { token } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function recheck() {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      onSynced(await api.syncApproach(token));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not read your solutions");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Solved, but not the intended way</h2>
        <button type="button" className="ghost" disabled={busy} onClick={recheck}>
          {busy ? "Reading solutions…" : "Re-check"}
        </button>
      </header>

      {data.checked === 0 ? (
        <p className="muted">
          Solvix has not read your solutions yet. Re-check reads each one from
          your LeetHub repo and compares it against the techniques the problem
          was tagged with.
        </p>
      ) : data.problems.length === 0 ? (
        /* A finding, not an absence: the solutions were read and none of them
           looked like a brute force. */
        <p className="muted">
          Nothing stands out. Of {data.checked} solutions read, none was
          accepted while avoiding every technique its problem was teaching.
        </p>
      ) : (
        <ul className="rows">
          {data.problems.map((p) => (
            <li key={p.problem_id} className="row row-alert">
              <div className="row-head row-head-cols">
                <a
                  className="row-title"
                  href={p.url}
                  target="_blank"
                  rel="noreferrer"
                >
                  {p.name}
                </a>
                <span className="badge">Brute forced</span>
                <span className="muted small">
                  Teaches {p.expected.join(", ")} — your solution uses{" "}
                  {p.used.length ? p.used.join(", ") : "none of them"}, with
                  nested loops.
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}

      {error && <p className="error small">{error}</p>}

      <p className="muted small skipped">
        Read from the solution code in your LeetHub repo. A problem is only
        listed when it uses none of the techniques it was tagged with *and*
        loops over loops — solving something a cleverer way is not a finding.
      </p>
    </section>
  );
}
