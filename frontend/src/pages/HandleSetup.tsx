import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import { useAuth } from "../auth";

export function HandleSetup({ onDone }: { onDone: () => Promise<void> }) {
  const { token, logout } = useAuth();
  const [handle, setHandle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await api.setHandle(token, handle.trim());
      // Import immediately: a dashboard with a handle but no data would just
      // send the user straight back here to press another button.
      await api.ingest(token);
      await onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save handle");
      setBusy(false);
    }
  }

  return (
    <div className="centered">
      <form className="card auth-card" onSubmit={onSubmit}>
        <h1 className="brand">One more thing</h1>
        <p className="muted">
          Enter your Codeforces handle so Solvix can import your submissions.
        </p>

        <label>
          Codeforces handle
          <input
            required
            value={handle}
            onChange={(e) => setHandle(e.target.value)}
            placeholder="tourist"
            autoFocus
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button type="submit" disabled={busy}>
          {busy ? "Importing…" : "Save and import"}
        </button>
        <button type="button" className="link" onClick={logout}>
          Log out
        </button>
      </form>
    </div>
  );
}
