import { useState, type FormEvent } from "react";

import { api } from "../api/client";
import { useAuth } from "../auth";
import { Logo } from "../components/Logo";
import { PasswordInput } from "../components/PasswordInput";
import { VersionFooter } from "../components/VersionFooter";
import { ThemeToggle } from "../components/ThemeToggle";

export function LoginPage() {
  const { login } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "register") {
        await api.register(email, password, displayName);
      }
      const token = await api.login(email, password);
      login(token.access_token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="centered">
      <form className="card auth-card" onSubmit={onSubmit}>
        <div className="topbar">
          <h1 className="brand-mark">
            <Logo height={36} />
          </h1>
          <ThemeToggle />
        </div>
        <p className="muted">Your competitive programming progress, measured.</p>

        {mode === "register" && (
          <label>
            Display name
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="optional"
            />
          </label>
        )}

        <label>
          Email
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>

        <PasswordInput
          label="Password"
          required
          minLength={8}
          autoComplete={mode === "login" ? "current-password" : "new-password"}
          value={password}
          onChange={setPassword}
        />

        {error && <p className="error">{error}</p>}

        {/* The label says what is happening, not that something is. "Working"
            is what a program says when it has not been told what it is doing —
            and on a host that can take fifty seconds to wake, the difference
            between "Signing in" and a shrug is the difference between waiting
            and reloading. */}
        <button type="submit" disabled={busy}>
          {busy
            ? mode === "login"
              ? "Signing in…"
              : "Creating your account…"
            : mode === "login"
              ? "Log in"
              : "Create account"}
        </button>

        {/* The question is context and the action is the link; underlining the
            whole sentence made a five-word phrase look like one long target. */}
        <p className="auth-switch">
          {mode === "login" ? "No account yet?" : "Already have an account?"}{" "}
          <button
            type="button"
            className="link inline"
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError(null);
            }}
          >
            {mode === "login" ? "Create one" : "Log in"}
          </button>
        </p>
      </form>
      {/* Also a quiet cold-start signal: the free API sleeps when idle, and a
          visitor who sees nothing happening assumes the site is broken. */}
      <VersionFooter />
    </div>
  );
}
