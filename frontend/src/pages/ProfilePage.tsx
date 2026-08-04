import { useRef, useState, type FormEvent } from "react";

import { ApiError, api } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../auth";
import { Avatar } from "../components/Avatar";
import { EmailChange } from "../components/EmailChange";

function message(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

export function ProfilePage({ onBack }: { onBack: () => void }) {
  const { user, token, refreshUser } = useAuth();
  if (!user || !token) return null;

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1 className="brand">Profile</h1>
          <span className="muted small">{user.email}</span>
        </div>
        <button className="ghost" onClick={onBack}>
          Back to dashboard
        </button>
      </header>

      <PhotoCard user={user} token={token} onSaved={refreshUser} />
      <DetailsCard user={user} token={token} onSaved={refreshUser} />
      <EmailChange user={user} token={token} onChanged={refreshUser} />
      <PasswordCard token={token} />
    </div>
  );
}

function PhotoCard({
  user,
  token,
  onSaved,
}: {
  user: User;
  token: string;
  onSaved: () => Promise<void>;
}) {
  const picker = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The avatar URL never changes, so a fresh upload would show the old blob
  // without something to tell the component to fetch again.
  const [version, setVersion] = useState(0);

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      await onSaved();
      setVersion((n) => n + 1);
    } catch (err) {
      setError(message(err, "Could not update your photo"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Photo</h2>
      </header>

      <div className="profile-photo">
        <Avatar user={user} size={88} version={version} />

        <div className="profile-photo-actions">
          <button
            type="button"
            className="pill-btn"
            disabled={busy}
            onClick={() => picker.current?.click()}
          >
            {busy ? "Working…" : user.has_avatar ? "Change photo" : "Upload photo"}
          </button>

          {user.has_avatar && (
            <button
              type="button"
              className="link"
              disabled={busy}
              onClick={() => void run(() => api.deleteAvatar(token))}
            >
              Remove
            </button>
          )}

          <p className="muted small">
            PNG, JPEG or WebP. Cropped to a square and stored at 256px.
          </p>
        </div>
      </div>

      <input
        ref={picker}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0];
          // Cleared straight away so choosing the same file twice in a row
          // still fires a change event.
          e.target.value = "";
          if (file) void run(() => api.uploadAvatar(token, file));
        }}
      />

      {error && <p className="error small skipped">{error}</p>}
    </section>
  );
}

function DetailsCard({
  user,
  token,
  onSaved,
}: {
  user: User;
  token: string;
  onSaved: () => Promise<void>;
}) {
  const [displayName, setDisplayName] = useState(user.display_name ?? "");
  const [handle, setHandle] = useState(user.codeforces_handle ?? "");
  const [leetcode, setLeetcode] = useState(user.leetcode_username ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const changed =
    displayName !== (user.display_name ?? "") ||
    handle !== (user.codeforces_handle ?? "") ||
    leetcode !== (user.leetcode_username ?? "");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      // Only what actually moved is sent: an unchanged field left out of the
      // request cannot be accidentally cleared by an empty input.
      await api.updateProfile(token, {
        ...(displayName !== (user.display_name ?? "")
          ? { display_name: displayName }
          : {}),
        ...(handle !== (user.codeforces_handle ?? "")
          ? { codeforces_handle: handle }
          : {}),
        ...(leetcode !== (user.leetcode_username ?? "")
          ? { leetcode_username: leetcode }
          : {}),
      });
      await onSaved();
      setSaved(true);
    } catch (err) {
      setError(message(err, "Could not save your details"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Details</h2>
      </header>

      <form className="profile-form" onSubmit={onSubmit}>
        <label>
          Display name
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="How Solvix should greet you"
          />
        </label>

        <label>
          Codeforces handle
          <input value={handle} onChange={(e) => setHandle(e.target.value)} />
        </label>

        <label>
          LeetCode username
          <input
            value={leetcode}
            onChange={(e) => setLeetcode(e.target.value)}
            placeholder="For your public solved totals"
          />
        </label>

        {/* Email is not here: it needs a verification round trip, so it has
            a card of its own rather than a field that saves with the rest. */}

        {error && <p className="error small">{error}</p>}
        {saved && !changed && <p className="notice small">Saved.</p>}

        <div className="form-actions">
          <button type="submit" disabled={busy || !changed}>
            {busy ? "Saving…" : "Save changes"}
          </button>
        </div>
      </form>
    </section>
  );
}

function PasswordCard({ token }: { token: string }) {
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setDone(false);

    // Checked here rather than on the server: the confirmation box exists to
    // catch a typo, and the server has no use for a second copy.
    if (next !== confirm) {
      setError("The two new passwords do not match");
      return;
    }

    setBusy(true);
    try {
      await api.changePassword(token, current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      setDone(true);
    } catch (err) {
      setError(message(err, "Could not change your password"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Password</h2>
      </header>

      <form className="profile-form" onSubmit={onSubmit}>
        <label>
          Current password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
        </label>

        <label>
          New password
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
        </label>

        <label>
          Confirm new password
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
        </label>

        {error && <p className="error small">{error}</p>}
        {done && <p className="notice small">Password changed.</p>}

        <div className="form-actions">
          <button type="submit" disabled={busy}>
            {busy ? "Changing…" : "Change password"}
          </button>
        </div>
      </form>
    </section>
  );
}
