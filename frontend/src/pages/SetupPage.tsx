import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";

import { ApiError, api } from "../api/client";
import { useAuth } from "../auth";
import { Logo } from "../components/Logo";
import { Reveal } from "../components/Reveal";

const REPO_PATTERN = /^[\w.-]+\/[\w.-]+$/;

type Step = "connect" | "import" | "ready";
type ImportState =
  | { status: "pending" }
  | { status: "running" }
  | { status: "done"; inserted: number }
  | { status: "failed"; reason: string };

function message(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

/** The first minute with a new account.
 *
 * It used to be a single box demanding a Codeforces handle before the
 * dashboard would render at all, then a dashboard of "not enough practice"
 * cards. Either platform can be the first connection now — the author's own
 * account is LeetCode-first — and the import happens here, with progress, so
 * the first screen after setup already has something on it.
 */
export function SetupPage() {
  const { token, user, refreshUser, logout } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState<Step>("connect");
  const [handle, setHandle] = useState(user?.codeforces_handle ?? "");
  const [repo, setRepo] = useState(user?.leetcode_repo ?? "");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [imports, setImports] = useState<Record<"codeforces" | "leetcode", ImportState>>({
    codeforces: { status: "pending" },
    leetcode: { status: "pending" },
  });

  const cleanRepo = repo.trim().replace(/^https:\/\/github\.com\//, "").replace(/\.git$/, "");
  const wantsCodeforces = handle.trim().length > 0;
  const wantsLeetcode = cleanRepo.length > 0;

  async function connect(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    if (!wantsCodeforces && !wantsLeetcode) {
      setError("Connect at least one platform to continue");
      return;
    }
    if (wantsLeetcode && !REPO_PATTERN.test(cleanRepo)) {
      setError("The LeetCode repo should look like owner/LeetCode-Problems");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      if (wantsCodeforces) await api.setHandle(token, handle.trim());
      if (wantsLeetcode) await api.setLeetcodeRepo(token, cleanRepo);
      setStep("import");
      void runImports();
    } catch (err) {
      setError(message(err, "Could not save your details"));
      setBusy(false);
    }
  }

  // One platform at a time, each reporting on its own line. A failure on one
  // does not stop the other: a typo in a repo name should not cost you the
  // Codeforces import that already worked.
  async function runImports() {
    if (!token) return;
    const order: ("codeforces" | "leetcode")[] = [];
    if (wantsCodeforces) order.push("codeforces");
    if (wantsLeetcode) order.push("leetcode");

    for (const platform of order) {
      setImports((s) => ({ ...s, [platform]: { status: "running" } }));
      try {
        const { inserted } =
          platform === "codeforces" ? await api.ingest(token) : await api.ingestLeetcode(token);
        setImports((s) => ({ ...s, [platform]: { status: "done", inserted } }));
      } catch (err) {
        setImports((s) => ({
          ...s,
          [platform]: { status: "failed", reason: message(err, "import failed") },
        }));
      }
    }
    await refreshUser();
    setBusy(false);
    setStep("ready");
  }

  const total = Object.values(imports).reduce(
    (n, s) => n + (s.status === "done" ? s.inserted : 0),
    0,
  );

  return (
    <div className="centered setup">
      <div className="setup-card card">
        <div className="topbar">
          <h1 className="brand-mark">
            <Logo height={30} />
          </h1>
          {step === "connect" && (
            <button type="button" className="link small" onClick={logout}>
              Log out
            </button>
          )}
        </div>

        <ol className="steps" aria-label="Setup progress">
          {(["connect", "import", "ready"] as Step[]).map((s, i) => {
            const idx = ["connect", "import", "ready"].indexOf(step);
            const state = i < idx ? "done" : i === idx ? "on" : "";
            return (
              <li key={s} className={`step ${state}`} aria-current={i === idx ? "step" : undefined}>
                <span className="step-num">{i < idx ? "✓" : i + 1}</span>
                <span className="step-name">{["Connect", "Import", "Ready"][i]}</span>
              </li>
            );
          })}
        </ol>

        {step === "connect" && (
          <Reveal>
            <form className="setup-body" onSubmit={connect}>
              <h2>Where do you practise?</h2>
              <p className="muted">
                Connect one or both. Solvix imports your history from here on —
                nothing to log by hand.
              </p>

              <div className="setup-panels">
                <label className="setup-panel">
                  <span className="setup-panel-title">Codeforces</span>
                  <span className="muted small">Your handle. Attempts and verdicts come from the public API.</span>
                  <input
                    value={handle}
                    onChange={(e) => setHandle(e.target.value)}
                    placeholder="tourist"
                    autoComplete="off"
                  />
                </label>
                <label className="setup-panel">
                  <span className="setup-panel-title">LeetCode</span>
                  <span className="muted small">
                    A GitHub repo kept by the{" "}
                    <a href="https://github.com/QasimWani/LeetHub" target="_blank" rel="noreferrer">
                      LeetHub
                    </a>{" "}
                    extension — LeetCode has no history API.
                  </span>
                  <input
                    value={repo}
                    onChange={(e) => setRepo(e.target.value)}
                    placeholder="owner/LeetCode-Problems"
                    autoComplete="off"
                  />
                </label>
              </div>

              {error && <p className="error small">{error}</p>}

              <div className="form-actions">
                <button type="submit" disabled={busy || (!wantsCodeforces && !wantsLeetcode)}>
                  {busy ? "Saving…" : "Continue"}
                </button>
              </div>
            </form>
          </Reveal>
        )}

        {step === "import" && (
          <Reveal>
            <div className="setup-body">
              <h2>Importing your history</h2>
              <p className="muted">
                A first import reads everything you have ever solved. It takes a
                moment; after this, mornings sync on their own.
              </p>
              <ImportRows imports={imports} wants={{ codeforces: wantsCodeforces, leetcode: wantsLeetcode }} />
            </div>
          </Reveal>
        )}

        {step === "ready" && (
          <Reveal>
            <div className="setup-body">
              <h2>{total > 0 ? "You're set." : "Connected."}</h2>
              <p className="muted">
                {total > 0
                  ? `${total.toLocaleString()} ${total === 1 ? "submission" : "submissions"} imported. Your dashboard is built from ${total === 1 ? "it" : "them"}.`
                  : "Nothing came through yet — you can sync again from the account menu once there is something to import."}
              </p>
              <ImportRows imports={imports} wants={{ codeforces: wantsCodeforces, leetcode: wantsLeetcode }} />
              <div className="form-actions">
                <button type="button" onClick={() => navigate("/", { replace: true })}>
                  Open my dashboard
                </button>
              </div>
            </div>
          </Reveal>
        )}
      </div>
    </div>
  );
}

function ImportRows({
  imports,
  wants,
}: {
  imports: Record<"codeforces" | "leetcode", ImportState>;
  wants: { codeforces: boolean; leetcode: boolean };
}) {
  const rows = (["codeforces", "leetcode"] as const).filter((p) => wants[p]);
  return (
    <ul className="import-rows" aria-live="polite">
      {rows.map((p) => {
        const s = imports[p];
        return (
          <li key={p} className={`import-row import-${s.status}`}>
            <span className="import-name">{p === "codeforces" ? "Codeforces" : "LeetCode"}</span>
            <span className="import-status muted small">
              {s.status === "pending" && "Waiting"}
              {s.status === "running" && (
                <>
                  <span className="thinking" aria-hidden="true"><i /><i /><i /></span> Importing…
                </>
              )}
              {s.status === "done" &&
                (s.inserted === 0 ? "Nothing new to import" : `${s.inserted.toLocaleString()} imported`)}
              {s.status === "failed" && `Failed — ${s.reason}`}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
