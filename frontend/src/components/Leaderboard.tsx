import type { Leaderboard as Data } from "../api/types";

/** This week's standings.
 *
 * Weekly rather than all-time, so the board is about the week you are in
 * rather than about who started first. With a small number of accounts that is
 * the difference between a contest and a wall.
 */
export function Leaderboard({ data }: { data: Data }) {
  if (!data.entries.length) {
    return (
      <section className="card">
        <header className="card-head">
          <h2>This week's board</h2>
        </header>
        <p className="muted">
          Nobody has solved anything yet this week. Solve one and you are top.
        </p>
      </section>
    );
  }

  const alone = data.total_ranked === 1;

  return (
    <section className="card">
      <header className="card-head">
        <h2>This week's board</h2>
        <span className="muted small">
          {/* Said plainly rather than hidden: a leaderboard of one looks
              broken unless it admits what it is. */}
          {alone
            ? "just you so far"
            : `${data.total_ranked} practising, resets Monday`}
        </span>
      </header>

      <ul className="rows">
        {data.entries.map((entry) => (
          <li
            key={`${entry.place}:${entry.name}`}
            className={entry.is_you ? "row row-todo" : "row"}
          >
            <div className="row-head board-row">
              <span className="board-place">{entry.place}</span>
              <span className="row-title">
                {entry.name}
                {entry.is_you && <span className="muted small"> · you</span>}
              </span>
              <span className="muted small">
                {entry.solved} solved · {entry.active_days}{" "}
                {entry.active_days === 1 ? "day" : "days"}
              </span>
            </div>
          </li>
        ))}
      </ul>

      {/* Only when it adds something: the caller is already highlighted in the
          list, so this line exists for the case where they placed outside the
          visible ten. */}
      {data.your_place !== null && data.your_place > data.entries.length && (
        <p className="muted small">You are {data.your_place}th this week.</p>
      )}
    </section>
  );
}
