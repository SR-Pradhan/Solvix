import { Link } from "react-router-dom";

import { Logo } from "../components/Logo";
import { Reveal } from "../components/Reveal";
import { ThemeToggle } from "../components/ThemeToggle";
import { VersionFooter } from "../components/VersionFooter";

/** A picture of the product, drawn with the product's own parts.
 *
 * A screenshot goes stale and carries whoever's data was on screen; this is
 * the real card and row styles with sample figures, so it matches the theme
 * the visitor chose and stays true as the design changes.
 */
function Preview() {
  return (
    <div className="preview" aria-hidden="true">
      <div className="preview-glow" />
      {/* Fictional figures. The first version quoted the author's own account,
          which read as a live dashboard shown to strangers — and was the
          author's personal data on a public page. */}
      <span className="preview-tag">Example dashboard</span>
      <div className="preview-frame">
        <section className="summary preview-summary">
          <div>
            <h2 className="summary-greeting">Good morning, Asha.</h2>
            <p className="summary-line muted">
              9-day streak. 2 things to revise. Focus:{" "}
              <strong>Two Pointers</strong>.
            </p>
          </div>
          <div className="summary-figures">
            <div className="summary-figure">
              <span className="summary-number">9</span>
              <span className="summary-label">day streak</span>
            </div>
            <div className="summary-figure">
              <span className="summary-number">132</span>
              <span className="summary-label">solved</span>
            </div>
          </div>
        </section>

        <section className="card">
          <header className="card-head">
            <h2>Are you still improving?</h2>
            <span className="muted small">last 21 days</span>
          </header>
          <ul className="rows">
            <li className="row row-alert">
              <div className="row-head row-head-cols">
                <span className="row-title">LeetCode</span>
                <span className="badge" style={{ color: "var(--danger)", borderColor: "var(--danger)" }}>
                  Coasting
                </span>
                <span className="muted small">
                  19 of your last 30 solves were below Medium.
                </span>
              </div>
            </li>
          </ul>
        </section>

        <section className="card">
          <header className="card-head">
            <h2>Solved, but not the intended way</h2>
          </header>
          <ul className="rows">
            <li className="row row-alert">
              <div className="row-head row-head-cols">
                <span className="row-title">Daily Temperatures</span>
                <span className="badge">Brute forced</span>
                <span className="muted small">
                  Teaches Monotonic Stack — your solution uses none of it, with nested loops.
                </span>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  );
}

/** The front door.
 *
 * Copy on the left, the product on the right. The first version was four
 * paragraphs and a bullet list — a wall of text selling a dashboard without
 * showing one. The argument is the screen itself, so the screen leads.
 */
export function LandingPage() {
  return (
    <div className="landing">
      <header className="topbar landing-top">
        <h1 className="brand-mark">
          <Logo height={34} />
        </h1>
        <div className="actions">
          <ThemeToggle />
          <Link className="ghost" to="/login">
            Log in
          </Link>
        </div>
      </header>

      <section className="hero hero-split">
        <Reveal>
          <div className="hero-copy">
            <p className="eyebrow">Codeforces + LeetCode</p>
            <h2 className="hero-title">
              Practice that knows what you're weak at.
            </h2>
            <p className="hero-sub muted">
              Solvix reads your submissions and your solution code, scores every
              topic, plans your day, and tells you what to revise. Nothing typed
              in by hand.
            </p>
            <div className="hero-actions">
              <Link className="cta" to="/login?mode=register">
                Create an account
              </Link>
              <Link className="ghost" to="/login">
                I have one
              </Link>
            </div>
          </div>
        </Reveal>
        <Reveal index={2}>
          <Preview />
        </Reveal>
      </section>

      <p className="muted small proof-caption">The kinds of things it says — illustrative figures.</p>
      <section className="proof-grid" aria-label="The kinds of findings Solvix makes">
        <Reveal index={3}>
          <div className="card proof-tile">
            <span className="proof-number">19<span className="proof-of">/30</span></span>
            <span className="proof-label">recent solves below a level already mastered</span>
            <span className="badge badge-warn badge-sentence">Coasting</span>
          </div>
        </Reveal>
        <Reveal index={4}>
          <div className="card proof-tile">
            <span className="proof-number">3<span className="proof-of"> loops</span></span>
            <span className="proof-label">where the problem was teaching a monotonic stack</span>
            <span className="badge badge-sentence" style={{ color: "var(--danger)", borderColor: "var(--danger)" }}>Brute forced</span>
          </div>
        </Reveal>
        <Reveal index={5}>
          <div className="card proof-tile">
            <span className="proof-number">13<span className="proof-of">%</span></span>
            <span className="proof-label">pass rate when two 75%+ techniques appear together</span>
            <span className="badge badge-sentence" style={{ color: "var(--danger)", borderColor: "var(--danger)" }}>Breaks down</span>
          </div>
        </Reveal>
      </section>

      <section className="features">
        <Reveal index={6}>
          <div className="feature-row">
            <span className="feature-mark" style={{ background: "var(--accent)" }} />
            <div>
              <h3>Derived, not logged</h3>
              <p className="muted">Every number comes from what the platforms already know. No form after a problem, nothing to forget.</p>
            </div>
          </div>
        </Reveal>
        <Reveal index={7}>
          <div className="feature-row">
            <span className="feature-mark" style={{ background: "var(--warn)" }} />
            <div>
              <h3>Weak topics, honestly scored</h3>
              <p className="muted">Accuracy and recency together — a tag you brute-forced or last touched months ago ranks weak, whatever the count.</p>
            </div>
          </div>
        </Reveal>
        <Reveal index={8}>
          <div className="feature-row">
            <span className="feature-mark" style={{ background: "var(--danger)" }} />
            <div>
              <h3>Reads your actual code</h3>
              <p className="muted">Accepted is not understood. Each solution is checked against the technique its problem was teaching.</p>
            </div>
          </div>
        </Reveal>
        <Reveal index={8}>
          <div className="feature-row">
            <span className="feature-mark" style={{ background: "var(--ok)" }} />
            <div>
              <h3>A plan, and a nudge</h3>
              <p className="muted">An agent plans each day from your weak spots. A 3 · 7 · 14 · 30 · 60-day ladder emails what to revisit.</p>
            </div>
          </div>
        </Reveal>
      </section>

      <VersionFooter />
    </div>
  );
}
