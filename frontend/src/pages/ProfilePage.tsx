import { useRef, useState, type FormEvent } from "react";

import { ApiError, api } from "../api/client";
import type { User } from "../api/types";
import { useAuth } from "../auth";
import { PasswordInput } from "../components/PasswordInput";
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
      <SecurityCard token={token} />
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
            {busy ? "Uploading…" : user.has_avatar ? "Change photo" : "Upload photo"}
          </button>

          {/* A button, not underlined text: it sits beside "Change photo" and
              does the same kind of thing, so it should look like it. */}
          {user.has_avatar && (
            <button
              type="button"
              className="pill-btn"
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
  const [repo, setRepo] = useState(user.leetcode_repo ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const changed =
    displayName !== (user.display_name ?? "") ||
    handle !== (user.codeforces_handle ?? "") ||
    leetcode !== (user.leetcode_username ?? "") ||
    repo !== (user.leetcode_repo ?? "");

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
        ...(repo !== (user.leetcode_repo ?? "") ? { leetcode_repo: repo } : {}),
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

        {/* Editable here at last. It used to be settable only from the
            dashboard's connect card, which disappears once it is set — so a
            typo in it could never be corrected. */}
        <label>
          LeetCode solutions repo
          <input
            value={repo}
            onChange={(e) => setRepo(e.target.value)}
            placeholder="owner/LeetCode-Problems"
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

/** Sessions, and the one action with no undo.
 *
 * Kept apart from the rest of the profile rather than mixed in with editing a
 * display name: these change who can reach the account, and one of them ends
 * it. Grouping them means nobody meets "Delete account" while looking for a
 * text field.
 */
function SecurityCard({ token }: { token: string }) {
  const { login, logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState("");

  async function signOutEverywhere() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      // A replacement token, so this tab survives. Logging you out of the
      // device in your hand to protect you from one that is not is a strange
      // bargain.
      const { access_token } = await api.revokeSessions(token);
      login(access_token);
      setNotice("Signed out everywhere else.");
    } catch (err) {
      setError(message(err, "Could not sign out the other sessions"));
    } finally {
      setBusy(false);
    }
  }

  async function deleteAccount() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteAccount(token, password);
      // No confirmation screen: the account it would belong to is gone.
      logout();
    } catch (err) {
      setError(message(err, "Could not delete your account"));
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <header className="card-head">
        <h2>Security</h2>
      </header>

      <div className="security-row">
        <div>
          <span className="row-title">Sign out everywhere else</span>
          <p className="muted small">
            Ends every other session and keeps this one. Useful if you signed in
            on a machine you no longer have.
          </p>
        </div>
        <button
          type="button"
          className="ghost"
          disabled={busy}
          onClick={signOutEverywhere}
        >
          Sign out others
        </button>
      </div>

      {notice && <p className="notice small">{notice}</p>}

      <div className="security-row danger-zone">
        <div>
          <span className="row-title">Delete account</span>
          <p className="muted small">
            Removes your account and everything in it — submissions, plans,
            reminders, interviews. This cannot be undone.
          </p>
        </div>
        {!confirming && (
          <button
            type="button"
            className="ghost danger"
            disabled={busy}
            onClick={() => setConfirming(true)}
          >
            Delete account
          </button>
        )}
      </div>

      {confirming && (
        <div className="profile-form">
          {/* The password is the point: a borrowed session must not be able to
              destroy an account, and it is the one thing a borrowed session
              does not have. */}
          <PasswordInput
            label="Confirm with your password"
            value={password}
            onChange={setPassword}
            autoComplete="current-password"
          />
          <div className="form-actions">
            <button
              type="button"
              className="danger"
              disabled={busy || !password}
              onClick={deleteAccount}
            >
              {busy ? "Deleting…" : "Delete my account permanently"}
            </button>
            <button
              type="button"
              className="ghost"
              disabled={busy}
              onClick={() => {
                setConfirming(false);
                setPassword("");
                setError(null);
              }}
            >
              Keep my account
            </button>
          </div>
        </div>
      )}

      {error && <p className="error small">{error}</p>}
    </section>
  );
}

function PasswordCard({ token }: { token: string }) {
  const { login } = useAuth();
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
      // The old token stopped being valid the moment the password changed,
      // so the replacement has to be stored or every later request 401s.
      const { access_token } = await api.changePassword(token, current, next);
      login(access_token);
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
        <PasswordInput
          label="Current password"
          required
          autoComplete="current-password"
          value={current}
          onChange={setCurrent}
        />

        <PasswordInput
          label="New password"
          required
          minLength={8}
          autoComplete="new-password"
          value={next}
          onChange={setNext}
        />

        <PasswordInput
          label="Confirm new password"
          required
          minLength={8}
          autoComplete="new-password"
          value={confirm}
          onChange={setConfirm}
        />

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
