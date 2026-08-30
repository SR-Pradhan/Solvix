import { useState } from "react";

import type { DailyPlan as Data } from "../api/types";

function totalMinutes(data: Data): number {
  return data.tasks.reduce((sum, t) => sum + t.minutes, 0);
}

export function DailyPlan({
  data,
  onRegenerate,
  busy,
}: {
  data: Data;
  onRegenerate: () => void;
  busy: boolean;
}) {
  // Declared before any early return: hooks must run in the same order on
  // every render, and this card starts life unavailable and becomes a real
  // plan once one is generated. Returning early above the hook changed the
  // hook count between those two renders, which crashes the card.
  const [showSteps, setShowSteps] = useState(false);

  if (data.unavailable) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>Today's plan</h2>
        </header>
        <p className="muted">{data.unavailable}</p>
      </section>
    );
  }

  const minutes = totalMinutes(data);

  return (
    <section className="card">
      <header className="card-head">
        <h2>Today's plan</h2>
        <span className="muted small">
          across all platforms
          {minutes > 0 ? `, about ${minutes} minutes` : ""}
        </span>
      </header>

      {data.focus.length > 0 && (
        <div className="chips">
          {data.focus.map((tag) => (
            <span key={tag} className="chip">
              {tag}
            </span>
          ))}
        </div>
      )}

      <ol className="rows rows-numbered">
        {data.tasks.map((task, i) => (
          <li key={i} className="row row-todo">
            <div className="row-head">
              <span className="row-title">{task.title}</span>
              <span className="muted small">{task.minutes}m</span>
            </div>
            {task.detail && <p className="muted small row-detail">{task.detail}</p>}
          </li>
        ))}
      </ol>

      {data.note && <p className="muted small plan-note">{data.note}</p>}

      {/* The reasoning is the difference between a plan and a horoscope: it
          says which of your numbers drove the choice, so a wrong plan can be
          argued with rather than merely ignored. */}
      {data.reasoning && (
        <p className="muted small plan-why">{data.reasoning}</p>
      )}

      {data.steps.length > 0 && (
        <div className="plan-steps">
          <button
            type="button"
            className=""
            onClick={() => setShowSteps(!showSteps)}
            aria-expanded={showSteps}
          >
            {showSteps ? "Hide" : "Show"} what it checked ({data.steps.length})
          </button>
          {/* Collapsed by default: it is provenance, wanted once and then
              trusted, not something to read every morning. */}
          {showSteps && (
            <ol className="muted small">
              {data.steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          )}
        </div>
      )}

      <button
        type="button"
        className="pill-btn plan-rebuild"
        onClick={onRegenerate}
        disabled={busy}
      >
        <svg
          viewBox="0 0 16 16"
          width="13"
          height="13"
          aria-hidden="true"
          className={busy ? "spin" : undefined}
        >
          <path
            d="M13.5 8a5.5 5.5 0 1 1-1.6-3.9M13.5 2v3h-3"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        {busy ? "Rebuilding…" : "Build a different plan"}
      </button>
    </section>
  );
}
