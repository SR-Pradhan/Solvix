"""Did you solve it the way the problem was asking?

Every other measure in Solvix takes "Accepted" at face value. This one does
not. LeetCode says whether the answer was right; it never says whether the
approach was the one being taught, and a brute force that squeaks past the time
limit is a problem you will fail again the moment an interviewer says "now do
it in O(n)".

The material is already there and was going unused: LeetHub commits the actual
solution file next to every problem, so the code can be read and compared
against the techniques LeetCode tagged the problem with.

**The naive version does not work.** "Tagged Hash Table, no HashMap in the
code" flags three real solutions out of the first five, all wrongly:

- `valid-anagram` is tagged Hash Table and counts with `int[26]`. That *is* a
  hash table, written as an array because the alphabet is fixed.
- `majority-element` is tagged Sorting, Hash Table and Counting, and the
  solution is Boyer-Moore voting — better than all three, and containing none
  of them.

So the rule is deliberately conservative, and needs **two** things to be true
before it says anything:

1. **None** of the techniques the problem was tagged with appear in the code —
   not merely the first one. A problem tagged four ways can be solved any of
   the four.
2. The code contains **nested iteration**. This is what separates "solved it a
   cleverer way" from "looped over everything twice". Boyer-Moore is a single
   pass, so it stays quiet; the triple loop over two arrays does not.

Both conditions are about avoiding false positives, because the cost of them is
not symmetrical here. A missed brute force is a lost insight. A wrongly accused
optimal solution teaches the reader to distrust the whole card.

**Only techniques that can be recognised honestly.** `PriorityQueue` in Java is
unambiguous; "two pointers" and "greedy" are shapes of thought with no reliable
textual signature. Those tags are skipped rather than guessed at — the same
rule the rest of the app follows when a platform does not know something.
"""

from __future__ import annotations

import re

# Techniques that leave an unmistakable mark in source code, per language.
# Written as regular expressions over the source with comments and strings
# already stripped, so a technique named in a comment cannot count as using it.
#
# The keys are LeetCode's own tag names, so no translation table is needed
# between what the platform says and what is looked for.
SIGNALS: dict[str, dict[str, list[str]]] = {
    "Hash Table": {
        "java": [r"\bHashMap\b", r"\bHashSet\b", r"\bMap\s*<", r"\bSet\s*<",
                 # A fixed-size frequency array is a hash table with the hash
                 # function inlined; counting it as one is not a concession.
                 r"new\s+int\s*\[\s*(26|128|256|10)\s*\]",
                 # An array used as a counter is a direct-address table — the
                 # hash function is just the index. `count[x][y]++` in
                 # detect-squares is a hash table with the hashing left out.
                 # Matching on the increment rather than the whole subscript:
                 # `count[point[0]][point[1]]++` nests brackets, which defeats
                 # any attempt to describe the index itself.
                 r"\]\s*\+\+"],
        "python": [r"\bdict\s*\(", r"\bset\s*\(", r"\bCounter\s*\(",
                   r"defaultdict", r"=\s*\{\s*\}"],
    },
    "Heap (Priority Queue)": {
        "java": [r"\bPriorityQueue\b"],
        "python": [r"\bheapq\b", r"heappush", r"heappop"],
    },
    "Stack": {
        "java": [r"\bStack\s*<", r"\bArrayDeque\b", r"\bDeque\s*<",
                 # StringBuilder driven from its end is a stack; `deleteCharAt`
                 # at the last index and `setLength` are the pop.
                 r"deleteCharAt", r"setLength\s*\("],
        "python": [r"\.append\s*\(.*\).*\.pop\s*\(\s*\)", r"\bdeque\s*\("],
    },
    "Monotonic Stack": {
        "java": [r"\bStack\s*<", r"\bArrayDeque\b", r"\bDeque\s*<",
                 # StringBuilder driven from its end is a stack; `deleteCharAt`
                 # at the last index and `setLength` are the pop.
                 r"deleteCharAt", r"setLength\s*\("],
        "python": [r"\bdeque\s*\("],
    },
    "Queue": {
        "java": [r"\bQueue\s*<", r"\bArrayDeque\b", r"\bLinkedList\s*<"],
        "python": [r"\bdeque\s*\("],
    },
    "Sorting": {
        "java": [r"Arrays\s*\.\s*sort", r"Collections\s*\.\s*sort", r"\.sort\s*\("],
        "python": [r"\.sort\s*\(", r"\bsorted\s*\("],
    },
    "Binary Search": {
        "java": [r"binarySearch", r"\bmid\b\s*="],
        "python": [r"\bbisect\b", r"\bmid\b\s*="],
    },
    "Trie": {
        "java": [r"\bTrie\b", r"children\s*\[", r"\bTrieNode\b"],
        "python": [r"\bTrie\b", r"children"],
    },
    "Union-Find": {
        "java": [r"\bfind\s*\(", r"\bunion\s*\(", r"\bparent\s*\["],
        "python": [r"\bfind\s*\(", r"\bunion\s*\(", r"\bparent\s*\["],
    },
    "Dynamic Programming": {
        "java": [r"\bdp\s*\[", r"\bmemo\b"],
        "python": [r"\bdp\s*\[", r"\bmemo\b", r"lru_cache", r"\bcache\b"],
    },
    "Backtracking": {
        "java": [r"\bbacktrack\s*\(", r"\bdfs\s*\("],
        "python": [r"\bbacktrack\s*\(", r"\bdfs\s*\("],
    },
    "Memoization": {
        "java": [r"\bmemo\b", r"\bdp\s*\["],
        "python": [r"\bmemo\b", r"lru_cache", r"\bcache\b"],
    },
    "Depth-First Search": {
        "java": [r"\bdfs\s*\(", r"\bbacktrack\s*\("],
        "python": [r"\bdfs\s*\(", r"\bbacktrack\s*\("],
    },
    "Breadth-First Search": {
        "java": [r"\bbfs\s*\(", r"\bQueue\s*<", r"\bArrayDeque\b"],
        "python": [r"\bbfs\s*\(", r"\bdeque\s*\("],
    },
}

# LeetHub names the file after the problem, so the extension is the language.
LANGUAGES = {
    ".java": "java",
    ".py": "python",
    ".py3": "python",
}

# Tags that are real techniques but have no honest textual signature: "greedy"
# and "two pointers" describe how you thought, not what you typed. Listed
# explicitly rather than merely absent from SIGNALS, so the distinction between
# "cannot be checked" and "not yet added" stays visible.
# Techniques whose correct, linear-time solution *looks* nested: a sliding
# window is a `for` with a `while` inside it, and so is a two-pointer sweep.
# The nesting test cannot tell those from a brute force, so when a problem is
# tagged with one of them the verdict is withheld rather than guessed. Being
# unable to judge is not the same as having judged badly.
NESTING_EXPLAINED_BY = frozenset({"Sliding Window", "Two Pointers"})

UNCHECKABLE = frozenset({
    "Greedy", "Two Pointers", "Sliding Window", "Math", "Array", "String",
    "Simulation", "Counting", "Prefix Sum", "Bit Manipulation", "Design",
    "Divide and Conquer", "Recursion", "Matrix", "Enumeration",
})


def language_of(filename: str) -> str | None:
    """Which language a solution file is written in, or None if unsupported."""
    for extension, language in LANGUAGES.items():
        if filename.lower().endswith(extension):
            return language
    return None


def strip_noise(code: str) -> str:
    """Remove comments and string literals before looking for techniques.

    Without this, a solution carrying `// could use a HashMap here` counts as
    using one, and the card's first finding is a lie.
    """
    code = re.sub(r"/\*.*?\*/", " ", code, flags=re.S)
    code = re.sub(r"//[^\n]*", " ", code)
    code = re.sub(r"#[^\n]*", " ", code)
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    code = re.sub(r"'(?:\\.|[^'\\])*'", "''", code)
    return code


def techniques_in(code: str, language: str) -> set[str]:
    """Every recognisable technique the source actually uses."""
    cleaned = strip_noise(code)
    found = set()
    for technique, by_language in SIGNALS.items():
        for pattern in by_language.get(language, []):
            if re.search(pattern, cleaned):
                found.add(technique)
                break
    return found


def has_nested_loops(code: str, language: str) -> bool:
    """Whether any loop is opened while another is already running.

    The brute-force tell. Tracked by nesting depth rather than by counting loop
    keywords, because two loops one after another are ordinary and two loops one
    inside the other are the thing worth noticing.
    """
    cleaned = strip_noise(code)

    if language == "python":
        # Indentation is the block structure, so a loop indented further than a
        # loop above it is inside it.
        depths: list[int] = []
        for line in cleaned.split("\n"):
            stripped = line.lstrip()
            if not stripped:
                continue
            indent = len(line) - len(stripped)
            while depths and indent <= depths[-1]:
                depths.pop()
            if re.match(r"(for|while)\b", stripped):
                if depths:
                    return True
                depths.append(indent)
        return False

    # Brace languages: walk the source tracking depth, remembering the depths at
    # which loops were opened.
    depth = 0
    loop_depths: list[int] = []
    index = 0
    pending_loop = False
    while index < len(cleaned):
        char = cleaned[index]
        if char == "{":
            depth += 1
            if pending_loop:
                loop_depths.append(depth)
                pending_loop = False
        elif char == "}":
            # Depth first, then discard the loops that lived inside the block
            # just closed. Popping before decrementing left a finished loop on
            # the stack, so three *sequential* loops read as nested ones.
            depth -= 1
            while loop_depths and loop_depths[-1] > depth:
                loop_depths.pop()
        elif re.match(r"(for|while)\b", cleaned[index:index + 6]):
            before = cleaned[index - 1] if index else " "
            if not (before.isalnum() or before == "_"):
                if loop_depths:
                    return True
                pending_loop = True
                index += 5
                continue
        index += 1
    return False


def review(tags: list[str], code: str, language: str) -> dict:
    """Judge one solved problem.

    `checkable` are the tagged techniques that can be recognised in source at
    all; a problem tagged only "Greedy" and "Array" yields no verdict, which is
    an honest outcome rather than a gap.
    """
    checkable = [tag for tag in tags if tag in SIGNALS]
    used = techniques_in(code, language)
    matched = sorted(used.intersection(checkable))
    nested = has_nested_loops(code, language)

    # Three conditions now: nothing the problem asked for appears in the
    # source, the source loops over loops, and the nesting is not explained by
    # a technique whose optimal form is nested anyway.
    excused = bool(NESTING_EXPLAINED_BY.intersection(tags))
    brute_forced = bool(checkable) and not matched and nested and not excused

    return {
        "checkable": sorted(checkable),
        "expected": sorted(checkable),
        "used": sorted(used),
        "matched": matched,
        "nested_loops": nested,
        "nesting_excused": excused,
        "brute_forced": brute_forced,
        "verdict": "Brute forced" if brute_forced else "As intended" if matched else "Not judged",
    }


# --- syncing and reading, below the pure logic above -----------------------

import asyncio

import httpx
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients import leethub_client
from app.core.config import settings
from app.db.models import SolutionReview, Submission

PLATFORM = "leetcode"
ACCEPTED = "OK"

# GitHub is being asked for one file per solved problem. Bounded so a large
# repo does not open a hundred sockets at once and get itself rate limited.
CONCURRENCY = 8


async def _review_one(
    client: httpx.AsyncClient, repo: str, token: str | None, slug: str, tags: list[str]
) -> dict | None:
    found = await leethub_client.fetch_solution_source(client, repo, slug, token)
    if found is None:
        return None

    filename, source = found
    language = language_of(filename)
    if language is None:
        # A language with no signals defined cannot be judged, and guessing
        # from a language we cannot read would be worse than staying quiet.
        return None

    verdict = review(tags, source, language)
    return {
        "external_problem_id": slug,
        "language": language,
        "verdict": verdict["verdict"],
        "expected": verdict["expected"],
        "used": verdict["used"],
    }


async def sync_reviews(db: AsyncSession, user_id: int, repo: str) -> dict:
    """Read every solved problem's source and store what it shows.

    Re-run rather than incremental: a solution can be rewritten in place, and
    the whole repo is a hundred small files. Cheap enough to redo, and simpler
    than working out which ones changed.
    """
    rows = (
        await db.execute(
            select(Submission.external_problem_id, Submission.tags)
            .where(
                Submission.user_id == user_id,
                Submission.platform == PLATFORM,
                Submission.verdict == ACCEPTED,
            )
            .distinct()
        )
    ).all()

    token = settings.github_token
    semaphore = asyncio.Semaphore(CONCURRENCY)

    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        async def guarded(slug: str, tags: list[str]):
            async with semaphore:
                return await _review_one(client, repo, token, slug, list(tags or []))

        results = await asyncio.gather(
            *(guarded(slug, tags) for slug, tags in rows), return_exceptions=True
        )

    stored = 0
    for result in results:
        # One unreachable file must not lose the other ninety-nine.
        if isinstance(result, Exception) or result is None:
            continue
        await db.execute(
            insert(SolutionReview)
            .values(user_id=user_id, platform=PLATFORM, **result)
            .on_conflict_do_update(
                constraint="uq_review_problem",
                set_={
                    "language": result["language"],
                    "verdict": result["verdict"],
                    "expected": result["expected"],
                    "used": result["used"],
                },
            )
        )
        stored += 1

    await db.commit()
    return await get_reviews(db, user_id)


async def get_reviews(db: AsyncSession, user_id: int, limit: int | None = None) -> dict:
    """Stored verdicts, worst first."""
    rows = (
        await db.execute(
            select(SolutionReview).where(SolutionReview.user_id == user_id)
        )
    ).scalars().all()

    flagged = [
        {
            "problem_id": r.external_problem_id,
            "name": r.external_problem_id.split("-", 1)[-1].replace("-", " ").title(),
            "language": r.language,
            "expected": list(r.expected or []),
            "used": list(r.used or []),
            "url": f"https://leetcode.com/problems/{_slug(r.external_problem_id)}/",
        }
        for r in rows
        if r.verdict == "Brute forced"
    ]
    flagged.sort(key=lambda item: item["problem_id"])

    return {
        "problems": flagged[:limit] if limit else flagged,
        "total_flagged": len(flagged),
        "reviewed": sum(1 for r in rows if r.verdict != "Not judged"),
        "checked": len(rows),
    }


def _slug(problem_id: str) -> str:
    """LeetCode's own slug, without LeetHub's numeric folder prefix."""
    head, _, tail = problem_id.partition("-")
    return tail if head.isdigit() and tail else problem_id
