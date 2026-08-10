import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import { useAuth } from "../auth";

const REPO_PATTERN = /^[\w.-]+\/[\w.-]+$/;

export function ConnectLeetCode({ onDone }: { onDone: () => Promise<void> }) {
  const { token } = useAuth();
  const [repo, setRepo] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;

    const trimmed = repo.trim().replace(/^https:\/\/github\.com\//, "").replace(/\.git$/, "");
    if (!REPO_PATTERN.test(trimmed)) {
      setError("Use the owner/repo form, e.g. your-name/LeetCode-Problems");
      return;
    }

    setBusy(true);
    setError(null);
    try {
      await api.setLeetcodeRepo(token, trimmed);
      await api.ingestLeetcode(token);
      await onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not import");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Connect LeetCode</h2>
      </header>
      {/* The extension is named here and nowhere else: this is the one screen
          where the reader has to act on it. Everywhere after this, what
          matters is what Solvix knows, not where it came from. */}
      <p className="muted small">
        LeetCode has no public API for your submission history, so Solvix reads
        it from a GitHub repository of your solutions. The{" "}
        <a
          href="https://github.com/QasimWani/LeetHub"
          target="_blank"
          rel="noreferrer"
        >
          LeetHub
        </a>{" "}
        browser extension keeps that repository up to date automatically.
      </p>
      <form className="inline-form" onSubmit={onSubmit}>
        <input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="owner/LeetCode-Problems"
          aria-label="GitHub repository holding your LeetCode solutions"
        />
        <button type="submit" disabled={busy}>
          {busy ? "Importing…" : "Import"}
        </button>
      </form>
      {error && <p className="error">{error}</p>}
    </section>
  );
}
