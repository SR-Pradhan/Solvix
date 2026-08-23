"""Finds technique *combinations* that are harder than their parts.

Weak-topic scoring already answers "which tags are you bad at". This answers a
different question, and the distinction is the whole reason the feature exists:
**which pairs of techniques break you when they appear together?**

The difference matters because a naive version of this is useless. Rank tag
pairs by accuracy alone and the list is just your weakest tag wearing eleven
different hats — `dp + trees`, `dp + graphs`, `dp + math`, all near the bottom
because `dp` is near the bottom. Every row is inherited from a parent you
already knew about, and the card tells you nothing the weak-topics card did
not.

So a pair only counts here when it is worse than *either* technique is on its
own:

    drop = min(accuracy_a, accuracy_b) - accuracy_together

Comparing against the **weaker** parent is the conservative test. If a pair
underperforms even the weaker of the two techniques that make it up, the
combination itself is doing the damage — it cannot be explained by "you are
bad at one of these". Comparing against the average or the stronger parent
would readmit exactly the inherited-weakness rows this is built to exclude.

**Codeforces only**, for the same reason accuracy is Codeforces-only
everywhere else in the app: LeetHub commits a solution only once it passes, so
every LeetCode row is accepted by construction. An accuracy drop cannot be
measured where recorded accuracy is always 100%. Rather than show a
meaningless zero, LeetCode is left out and the UI says so.
"""

from __future__ import annotations

from sqlalchemy import distinct, func, select, true
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Submission

ACCEPTED = "OK"

# Accuracy is only a signal on platforms that record failed attempts.
PLATFORM = "codeforces"

# A pair needs more evidence than a single tag does. One bad afternoon on three
# problems is not a pattern, and this list is meant to be short and trusted
# rather than long and hedged — a false row here sends someone off to practise
# a weakness they do not have.
MIN_PAIR_ATTEMPTS = 12

# The baseline each parent is judged against has to be stable too: if a tag's
# solo accuracy rests on four attempts, the "drop" is measuring the noise in
# that baseline rather than anything about the combination.
MIN_SOLO_ATTEMPTS = 8

# Below this the gap is ordinary variance rather than a real interaction. Tuned
# against real data: at 0.15 an active account surfaces a dozen or so pairs,
# which is a list worth reading; dropping it to 0.05 surfaced closer to a
# hundred and most of them were noise.
MIN_DROP = 0.15

# Plain-language bands, so the UI never shows a raw score. Named for how the
# combination behaves, not how bad it is.
SEVERITY_BANDS = ((0.30, "Breaks down"), (0.20, "Struggles"), (0.0, "Slips"))


def severity_for(drop: float) -> str:
    """Band a drop, judged on the figure the UI actually shows.

    Rounded to two places first because that is the precision the card
    displays as a percentage. A raw drop of 0.2996 renders as "30%" and would
    otherwise be labelled one band below what the reader can see, which looks
    like a bug even though the arithmetic is right.
    """
    shown = round(drop, 2)
    for threshold, label in SEVERITY_BANDS:
        if shown >= threshold:
            return label
    return "Slips"


def interaction_drop(
    pair_accuracy: float, solo_a: float, solo_b: float
) -> float:
    """How much worse the combination is than its weaker half.

    Negative when the pair does *better* than its parts, which is a real and
    unremarkable outcome — two techniques that cue each other. Callers filter
    those out rather than showing "you are unusually good at this", which is
    not what anyone opened a practice tracker to find out.
    """
    return round(min(solo_a, solo_b) - pair_accuracy, 4)


def find_patterns(
    pairs: list[dict],
    solo: dict[str, dict],
    limit: int | None = None,
) -> dict:
    """Rank tag pairs by interaction drop.

    `pairs` carries one row per co-occurring tag pair with its own attempts and
    accuracy; `solo` maps each tag to its standalone figures. Kept a pure
    function so the ranking can be tested without a database — the query that
    feeds it is below.
    """
    found = []
    considered = 0

    for pair in pairs:
        a, b = pair["tags"]
        first, second = solo.get(a), solo.get(b)

        # A pair whose parents have no stable baseline cannot be judged. It is
        # not evidence of anything either way, so it is skipped rather than
        # counted as passing.
        if first is None or second is None:
            continue
        if pair["attempts"] < MIN_PAIR_ATTEMPTS:
            continue

        considered += 1
        drop = interaction_drop(
            pair["accuracy"], first["accuracy"], second["accuracy"]
        )
        if drop < MIN_DROP:
            continue

        found.append(
            {
                "tags": [a, b],
                "attempts": pair["attempts"],
                "solved": pair["solved"],
                "accuracy": round(pair["accuracy"], 4),
                # What the weaker parent alone would have predicted, so the UI
                # can show the comparison the score is actually built on.
                "expected": round(min(first["accuracy"], second["accuracy"]), 4),
                "drop": drop,
                "severity": severity_for(drop),
                "parts": [
                    {"tag": a, "accuracy": round(first["accuracy"], 4)},
                    {"tag": b, "accuracy": round(second["accuracy"], 4)},
                ],
            }
        )

    # Biggest drop first. Ties break on attempts, so where two pairs look
    # equally bad the better-evidenced one leads; then on tags, so the order is
    # stable rather than dependent on how the rows came back.
    found.sort(key=lambda p: (-p["drop"], -p["attempts"], p["tags"]))

    return {
        "patterns": found[:limit] if limit else found,
        "total_found": len(found),
        "pairs_considered": considered,
        "min_attempts": MIN_PAIR_ATTEMPTS,
        "platform": PLATFORM,
    }


async def _solo_accuracy(db: AsyncSession, user_id: int) -> dict[str, dict]:
    """Standalone accuracy per tag — the baseline each pair is judged against."""
    tag = func.unnest(Submission.tags).label("tag")
    tagged = (
        select(tag, Submission.verdict.label("verdict"))
        .where(Submission.user_id == user_id, Submission.platform == PLATFORM)
        .subquery()
    )

    rows = (
        await db.execute(
            select(
                tagged.c.tag,
                func.count().label("attempts"),
                func.count().filter(tagged.c.verdict == ACCEPTED).label("accepted"),
            )
            .group_by(tagged.c.tag)
            .having(func.count() >= MIN_SOLO_ATTEMPTS)
        )
    ).all()

    return {
        row.tag: {"attempts": row.attempts, "accuracy": row.accepted / row.attempts}
        for row in rows
    }


async def _pair_accuracy(db: AsyncSession, user_id: int) -> list[dict]:
    """Accuracy for every co-occurring pair of tags.

    Two lateral joins rather than two `unnest` calls in the select list: since
    Postgres 10 multiple set-returning functions in a select list are *zipped*
    positionally, which would pair each tag with itself and silently return
    nothing. `a.tag < b.tag` both removes the self-pairs and keeps one row per
    unordered pair instead of two.

    `render_derived` is what supplies the `AS name(tag)` column list. Without
    it the alias names the table but leaves the column called `unnest`, and
    Postgres rejects the query outright. `.lateral()` has to be applied here
    rather than at the join, because it returns a *new* alias — joining
    `first.lateral()` while selecting `first.c.tag` puts both in the FROM
    clause and quietly cross-joins four unnests instead of two.
    """
    first = (
        func.unnest(Submission.tags)
        .table_valued("tag")
        .render_derived(name="tag_a")
        .lateral()
    )
    second = (
        func.unnest(Submission.tags)
        .table_valued("tag")
        .render_derived(name="tag_b")
        .lateral()
    )

    rows = (
        await db.execute(
            select(
                first.c.tag.label("a"),
                second.c.tag.label("b"),
                func.count().label("attempts"),
                func.count().filter(Submission.verdict == ACCEPTED).label("accepted"),
                func.count(distinct(Submission.external_problem_id))
                .filter(Submission.verdict == ACCEPTED)
                .label("solved"),
            )
            .select_from(Submission)
            .join(first, true())
            .join(second, true())
            .where(
                first.c.tag < second.c.tag,
                Submission.user_id == user_id,
                Submission.platform == PLATFORM,
            )
            .group_by(first.c.tag, second.c.tag)
            .having(func.count() >= MIN_PAIR_ATTEMPTS)
        )
    ).all()

    return [
        {
            "tags": [row.a, row.b],
            "attempts": row.attempts,
            "solved": row.solved,
            "accuracy": row.accepted / row.attempts,
        }
        for row in rows
    ]


async def get_patterns(
    db: AsyncSession, user_id: int, limit: int | None = None
) -> dict:
    """Technique combinations that underperform both of their parts."""
    solo = await _solo_accuracy(db, user_id)
    # Nothing to compare against, so there is no need to expand the pairs at
    # all — this is the common case for an account with only LeetCode data.
    if not solo:
        return find_patterns([], {}, limit=limit)

    pairs = await _pair_accuracy(db, user_id)
    return find_patterns(pairs, solo, limit=limit)
