import { useEffect, useState, type FormEvent } from "react";

import { ApiError, api } from "../api/client";
import type { PendingEmailChange, User } from "../api/types";

function message(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

/**
 * Changing the account's email address, in two legs.
 *
 * The password proves the person asking owns the account; the code proves
 * they can read mail at the new address. Neither alone is enough, which is
 * why this is not just another field in the details form.
 */
export function EmailChange({
  user,
  token,
  onChanged,
}: {
  user: User;
  token: string;
  onChanged: () => Promise<void>;
}) {
  const [pending, setPending] = useState<PendingEmailChange | null>(null);
  const [loaded, setLoaded] = useState(false);

  // A request survives a page reload, so the code entry screen has to be
  // recoverable rather than living only in component state.
  useEffect(() => {
    let cancelled = false;
    api
      .pendingEmailChange(token)
      .then((result) => !cancelled && setPending(result))
      .catch(() => undefined)
      .finally(() => !cancelled && setLoaded(true));
    return () => {
      cancelled = true;
    };
  }, [token]);

  return (
    <section className="card">
      <header className="card-head">
        <h2>Email</h2>
        <span className="muted small">{user.email}</span>
      </header>

      {!loaded ? (
        <p className="muted small">Loading…</p>
      ) : pending ? (
        <VerifyStep
          token={token}
          pending={pending}
          onPending={setPending}
          onVerified={async () => {
            setPending(null);
            await onChanged();
          }}
        />
      ) : (
        <RequestStep token={token} onRequested={setPending} />
      )}
    </section>
  );
}

function RequestStep({
  token,
  onRequested,
}: {
  token: string;
  onRequested: (pending: PendingEmailChange) => void;
}) {
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onRequested(await api.requestEmailChange(token, newEmail, password));
      setPassword("");
    } catch (err) {
      setError(message(err, "Could not start the change"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="profile-form" onSubmit={onSubmit}>
      <label>
        New email address
        <input
          type="email"
          required
          autoComplete="email"
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
        />
      </label>

      <label>
        Current password
        <input
          type="password"
          required
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>

      <p className="muted small">
        Solvix sends a six digit code to the new address. Your email only
        changes once you enter it.
      </p>

      {error && <p className="error small">{error}</p>}

      <div className="form-actions">
        <button type="submit" disabled={busy}>
          {busy ? "Sending…" : "Send code"}
        </button>
      </div>
    </form>
  );
}

function VerifyStep({
  token,
  pending,
  onPending,
  onVerified,
}: {
  token: string;
  pending: PendingEmailChange;
  onPending: (pending: PendingEmailChange | null) => void;
  onVerified: () => Promise<void>;
}) {
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resendIn, setResendIn] = useState(pending.resend_in_seconds);
  const [resending, setResending] = useState(false);

  // Counted down in the browser rather than re-asking the server every
  // second; the server still refuses an early resend either way.
  useEffect(() => {
    if (resendIn <= 0) return;
    const timer = setInterval(() => setResendIn((n) => Math.max(0, n - 1)), 1000);
    return () => clearInterval(timer);
  }, [resendIn]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.verifyEmailChange(token, code);
      await onVerified();
    } catch (err) {
      setCode("");
      setError(message(err, "Could not confirm the code"));
    } finally {
      setBusy(false);
    }
  }

  async function resend() {
    setResending(true);
    setError(null);
    try {
      const next = await api.requestEmailChange(
        token,
        pending.new_email,
        password,
      );
      onPending(next);
      setResendIn(next.resend_in_seconds);
      setPassword("");
    } catch (err) {
      setError(message(err, "Could not send another code"));
    } finally {
      setResending(false);
    }
  }

  async function cancel() {
    try {
      await api.cancelEmailChange(token);
    } finally {
      onPending(null);
    }
  }

  return (
    <form className="profile-form" onSubmit={onSubmit}>
      <p className="muted small" style={{ margin: 0 }}>
        A code was sent to <strong>{pending.new_email}</strong>. It expires in
        ten minutes.
      </p>

      <label>
        Six digit code
        <input
          className="code-input"
          inputMode="numeric"
          autoComplete="one-time-code"
          pattern="\d{6}"
          maxLength={6}
          required
          value={code}
          // Stripped as you type: pasting a code out of an email often
          // brings a space or a stray character with it.
          onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
        />
      </label>

      {resendIn === 0 && (
        <label>
          Current password
          <input
            type="password"
            autoComplete="current-password"
            placeholder="Needed only to send another code"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
      )}

      {error && <p className="error small">{error}</p>}

      <div className="form-actions email-actions">
        <button type="submit" disabled={busy || code.length !== 6}>
          {busy ? "Checking…" : "Confirm"}
        </button>

        {resendIn > 0 ? (
          <span className="muted small">Resend in {resendIn}s</span>
        ) : (
          <button
            type="button"
            className="link"
            disabled={resending || !password}
            onClick={() => void resend()}
          >
            {resending ? "Sending…" : "Send another code"}
          </button>
        )}

        <button type="button" className="link" onClick={() => void cancel()}>
          Cancel
        </button>
      </div>
    </form>
  );
}
