import { useEffect, useRef, useState, type FormEvent } from "react";

import { ApiError, api } from "../api/client";
import type { Interview } from "../api/types";
import { useAuth } from "../auth";

function message(err: unknown, fallback: string): string {
  return err instanceof ApiError ? err.message : fallback;
}

/** How often complexity came up, across finished interviews.
 *
 * The point of keeping the findings at all. One interview's feedback is a
 * model's opinion; the same gap four sessions running is a fact about you —
 * and it is the one thing neither platform can measure, because they know
 * whether you solved something, never whether you could explain it.
 */
function complexityRate(history: Interview[]): string | null {
  const judged = history.filter((i) => i.findings);
  if (judged.length < 2) return null;
  const covered = judged.filter((i) => i.findings?.complexity_handled).length;
  return `Complexity covered in ${covered} of your last ${judged.length}`;
}

function PastInterviews({
  history,
  onOpen,
}: {
  history: Interview[];
  onOpen: (interview: Interview) => void;
}) {
  if (!history.length) return null;
  const rate = complexityRate(history);

  return (
    <section className="card">
      <header className="card-head">
        <h2>Past interviews</h2>
        {rate && <span className="muted small">{rate}</span>}
      </header>

      <ul className="interview-list">
        {history.map((item) => (
          <li key={item.id}>
            {/* The whole row opens it: a transcript is the reason to click,
                and a small link inside a wide row is a target you miss. */}
            <button type="button" onClick={() => onOpen(item)}>
              <span className="interview-row-head">
                <span className="interview-problem">{item.problem_name}</span>
                <span className="muted small">
                  {item.topic}
                  {item.created_at
                    ? ` · ${new Date(item.created_at).toLocaleDateString(undefined, {
                        day: "numeric",
                        month: "short",
                      })}`
                    : ""}
                </span>
              </span>
              <span className="muted small interview-verdict">
                {item.findings?.verdict}
              </span>
              <span
                className={
                  item.findings?.complexity_handled
                    ? "badge badge-sentence badge-ok"
                    : "badge badge-sentence badge-warn"
                }
              >
                {item.findings?.complexity_handled
                  ? "Complexity covered"
                  : "Complexity missed"}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function InterviewPage({ onBack }: { onBack: () => void }) {
  const { token } = useAuth();
  const [interview, setInterview] = useState<Interview | null>(null);
  const [history, setHistory] = useState<Interview[]>([]);
  const [answer, setAnswer] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endOfTurns = useRef<HTMLDivElement>(null);

  // Follow the conversation as it grows, the way any chat does — otherwise the
  // newest question appears below the fold and the page looks stuck.
  useEffect(() => {
    endOfTurns.current?.scrollIntoView({ behavior: "smooth" });
  }, [interview?.turns.length]);

  // Reloaded whenever a session ends rather than only on mount, so a finished
  // interview appears in the list without a refresh.
  useEffect(() => {
    if (!token) return;
    api
      .listInterviews(token)
      .then((r) => setHistory(r.interviews.filter((i) => i.findings)))
      .catch(() => setHistory([]));
  }, [token, interview?.status]);

  async function run(action: () => Promise<Interview>) {
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      setInterview(await action());
    } catch (err) {
      setError(message(err, "Something went wrong"));
    } finally {
      setBusy(false);
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = answer.trim();
    if (!text || !interview) return;
    // Cleared before the request, not after: the answer is already on its way,
    // and leaving it in the box invites sending it twice.
    setAnswer("");
    await run(() => api.replyToInterview(token!, interview.id, text));
  }

  if (!interview) {
    return (
      <div className="page">
        <header className="topbar">
          <div>
            <h1 className="brand">Mock interview</h1>
            <span className="muted small">
              A problem from a topic you are weak on, and someone asking why
            </span>
          </div>
          <button className="ghost" onClick={onBack}>
            Back to dashboard
          </button>
        </header>

        <section className="card">
          <p className="muted">
            Solvix picks a problem you have never solved, from one of your
            weakest topics. Talk through your approach before writing code —
            that is what gets probed.
          </p>
          {error && <p className="error small">{error}</p>}
          <div className="form-actions">
            <button
              type="button"
              disabled={busy}
              onClick={() => run(() => api.startInterview(token!))}
            >
              {busy ? "Finding a problem…" : "Start an interview"}
            </button>
          </div>
        </section>

        <PastInterviews history={history} onOpen={setInterview} />
      </div>
    );
  }

  const finished = interview.status === "finished";
  // Nothing to assess until they have actually said something, so ending is
  // offered only once there is a transcript worth reviewing. Before that the
  // honest action is to walk away, not to be graded on silence.
  const hasAnswered = interview.turns.some((t) => t.role === "user");

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <h1 className="brand">Mock interview</h1>
          <span className="muted small">
            {interview.topic}
            {interview.problem_name ? ` · ${interview.problem_name}` : ""}
          </span>
        </div>
        <div className="actions">
          {interview.problem_url && (
            <a
              className="ghost"
              href={interview.problem_url}
              target="_blank"
              rel="noreferrer"
            >
              Open the problem
            </a>
          )}
          <button className="ghost" onClick={onBack}>
            Back to dashboard
          </button>
        </div>
      </header>

      <section className="card">
        <div className="interview-turns">
          {interview.turns.map((turn, i) => (
            <div
              key={i}
              className={turn.role === "user" ? "turn turn-you" : "turn turn-them"}
            >
              <span className="muted small turn-who">
                {turn.role === "user" ? "You" : "Interviewer"}
              </span>
              <p>{turn.content}</p>
            </div>
          ))}
          <div ref={endOfTurns} />
        </div>

        {error && <p className="error small">{error}</p>}

        {!finished && (
          <form className="interview-answer" onSubmit={onSubmit}>
            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Talk through your thinking…"
              rows={3}
              disabled={busy}
              onKeyDown={(e) => {
                // Enter sends, Shift+Enter breaks the line. Typing an approach
                // runs to several sentences, so the newline has to stay
                // reachable.
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void onSubmit(e as unknown as FormEvent);
                }
              }}
            />
            <div className="form-actions">
              <button type="submit" disabled={busy || !answer.trim()}>
                {busy ? "Thinking…" : "Send"}
              </button>
              {hasAnswered ? (
                <button
                  type="button"
                  className="ghost"
                  disabled={busy}
                  onClick={() => run(() => api.finishInterview(token!, interview.id))}
                >
                  End and get feedback
                </button>
              ) : (
                <button
                  type="button"
                  className="ghost"
                  disabled={busy}
                  onClick={async () => {
                    if (!token) return;
                    // Discarded rather than kept: an interview nobody answered
                    // is not a practice record, and keeping it would pad the
                    // history with non-events.
                    await api.abandonInterview(token, interview.id).catch(() => {});
                    setInterview(null);
                  }}
                >
                  Leave this one
                </button>
              )}
            </div>
          </form>
        )}
      </section>

      {finished && interview.findings && (
        <section className="card">
          <header className="card-head">
            <h2>How it went</h2>
            <span
              className={
                interview.findings.complexity_handled
                  ? "badge badge-sentence badge-ok"
                  : "badge badge-sentence badge-warn"
              }
            >
              {interview.findings.complexity_handled
                ? "Complexity covered"
                : "Complexity not covered"}
            </span>
          </header>

          <p>{interview.findings.verdict}</p>

          {interview.findings.strengths.length > 0 && (
            <>
              <h3 className="small">Went well</h3>
              <ul className="muted small">
                {interview.findings.strengths.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          )}

          {interview.findings.gaps.length > 0 && (
            <>
              <h3 className="small">Worth working on</h3>
              <ul className="muted small">
                {interview.findings.gaps.map((g, i) => (
                  <li key={i}>{g}</li>
                ))}
              </ul>
            </>
          )}

          {interview.findings.advice && (
            <p className="notice small">{interview.findings.advice}</p>
          )}

          <div className="form-actions">
            <button
              type="button"
              disabled={busy}
              onClick={() => {
                setInterview(null);
                setAnswer("");
              }}
            >
              Another one
            </button>
          </div>
        </section>
      )}
    </div>
  );
}
