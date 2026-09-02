import { Link } from "react-router-dom";

import { Logo } from "../components/Logo";
import { Reveal } from "../components/Reveal";
import { ThemeToggle } from "../components/ThemeToggle";
import { VersionFooter } from "../components/VersionFooter";

/** The front door.
 *
 * Until this existed the first screen anyone saw was a login form, and the
 * argument for the product lived in the README — which somebody opening the
 * live link never reads. This says what Solvix does and what it has found,
 * then asks for an account.
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

      <Reveal>
        <section className="hero">
          <p className="eyebrow">For placement prep on Codeforces and LeetCode</p>
          <h2 className="hero-title">
            Practice that knows what you are weak at.
          </h2>
          <p className="hero-sub muted">
            Solvix reads your submission history and your solution code, scores
            every topic, plans each day, and reminds you what to revise — with
            nothing typed in by hand.
          </p>
          <div className="hero-actions">
            <Link className="cta" to="/login?mode=register">
              Create an account
            </Link>
            <Link className="ghost" to="/login">
              I have one
            </Link>
          </div>
        </section>
      </Reveal>

      <div className="landing-grid">
        <Reveal index={1}>
          <section className="card feature">
            <h3>Derived, not logged</h3>
            <p className="muted">
              Every number comes from what the platforms already know. There is
              no form to fill in after a problem, so there is nothing to forget.
            </p>
          </section>
        </Reveal>
        <Reveal index={2}>
          <section className="card feature">
            <h3>Weak topics, honestly scored</h3>
            <p className="muted">
              Accuracy and recency together — a tag you brute-forced through
              or last touched months ago ranks as weak, even with many solves.
            </p>
          </section>
        </Reveal>
        <Reveal index={3}>
          <section className="card feature">
            <h3>Reads your actual code</h3>
            <p className="muted">
              Accepted is not understood. Solvix checks whether each solution
              used the technique the problem was teaching, or looped past it.
            </p>
          </section>
        </Reveal>
        <Reveal index={4}>
          <section className="card feature">
            <h3>A plan, and a nudge</h3>
            <p className="muted">
              An agent plans each day from your weak spots, and a spaced ladder
              — 3, 7, 14, 30, 60 days — emails you what to revisit each morning.
            </p>
          </section>
        </Reveal>
      </div>

      <Reveal index={5}>
        <section className="card proof">
          <h3>What it has said to its author</h3>
          <ul className="proof-list">
            <li>
              <strong>Coasting.</strong> 28 of the last 52 solves were Easy, with
              50 Mediums already behind them and one Hard.
            </li>
            <li>
              <strong>Brute forced.</strong> A problem tagged <em>monotonic stack</em>,
              accepted with three nested loops.
            </li>
            <li>
              <strong>Breaks down.</strong> 79% on implementation, 55% on
              probabilities — 13% when a problem needs both.
            </li>
          </ul>
        </section>
      </Reveal>

      <VersionFooter />
    </div>
  );
}
