from app.clients.leethub_client import parse_problem_readme, parse_tag_map

# Trimmed from a real LeetHub 2.0 repo.
ROOT_README = """# LeetCode-Problems
A collection of LeetCode questions to ace the coding interview!

<!---LeetCode Topics Start-->
# LeetCode Topics
## Array
|  |
| ------- |
| [0001-two-sum](https://github.com/u/r/tree/master/0001-two-sum) |
| [0015-3sum](https://github.com/u/r/tree/master/0015-3sum) |
## Hash Table
|  |
| ------- |
| [0001-two-sum](https://github.com/u/r/tree/master/0001-two-sum) |
## Two Pointers
|  |
| ------- |
| [0015-3sum](https://github.com/u/r/tree/master/0015-3sum) |
"""

PROBLEM_README = (
    '<h2><a href="https://leetcode.com/problems/two-sum">1. Two Sum</a></h2>'
    "<h3>Easy</h3><hr><p>Given an array of integers...</p>"
)


def test_tag_map_collects_every_tag_for_a_problem():
    tags = parse_tag_map(ROOT_README)
    assert tags["0001-two-sum"] == ["Array", "Hash Table"]
    assert tags["0015-3sum"] == ["Array", "Two Pointers"]


def test_tag_map_skips_the_topics_heading():
    assert "LeetCode Topics" not in parse_tag_map(ROOT_README)


def test_tag_map_of_a_repo_with_no_topics_section():
    assert parse_tag_map("# Just a readme\n\nNothing here.") == {}


def test_problem_readme_gives_title_and_difficulty():
    assert parse_problem_readme(PROBLEM_README) == ("Two Sum", "Easy")


def test_problem_number_is_stripped_from_the_title():
    readme = '<h2><a href="https://leetcode.com/problems/x">1235. Maximum Profit</a></h2><h3>Hard</h3>'
    title, difficulty = parse_problem_readme(readme)
    assert title == "Maximum Profit"
    assert difficulty == "Hard"


def test_missing_difficulty_is_none_rather_than_a_crash():
    title, difficulty = parse_problem_readme(
        '<h2><a href="https://leetcode.com/problems/x">7. Reverse</a></h2><p>text</p>'
    )
    assert title == "Reverse"
    assert difficulty is None


def test_unparseable_readme_yields_nones():
    assert parse_problem_readme("just some text") == (None, None)


# --- reconciling the two id shapes ---

from app.services.leetcode_ingestion_service import not_yet_imported


def test_a_problem_the_profile_already_imported_is_not_imported_again():
    # The bug this exists for: the profile stores "reverse-bits", the repo
    # offers "0190-reverse-bits", and comparing the raw strings made the second
    # look new — so one problem was stored twice, inflating the solved count
    # and producing two revision schedules for it.
    assert not_yet_imported(["0190-reverse-bits"], {"reverse-bits"}) == []


def test_the_reverse_direction_still_works():
    assert not_yet_imported(["0190-reverse-bits"], {"0190-reverse-bits"}) == []


def test_a_genuinely_new_problem_is_kept():
    assert not_yet_imported(["0001-two-sum"], {"reverse-bits"}) == ["0001-two-sum"]


def test_the_folder_name_is_what_gets_returned():
    # The caller imports from the repo, so it needs the folder name back, not
    # the slug it was compared on.
    assert not_yet_imported(["0001-two-sum"], set()) == ["0001-two-sum"]


def test_nothing_stored_means_everything_is_new():
    folders = ["0001-two-sum", "0190-reverse-bits"]
    assert not_yet_imported(folders, set()) == folders


# --- repeat solves ------------------------------------------------------------
#
# Written after a 12-day streak that should have been 15. The repo held solution
# commits on 19 and 21 Aug that Solvix had never seen, because every one was a
# *modified* file — a problem solved again — and the import kept only each
# folder's first commit.

from datetime import datetime

from app.clients.leethub_client import (
    is_solution_commit,
    slug_from_path,
    solve_events,
)


def commit(sha, message, when="2026-08-19T06:23:00Z"):
    return {"sha": sha, "commit": {"message": message, "author": {"date": when}}}


def test_only_the_runtime_commit_is_a_solve():
    # LeetHub writes two commits per accepted answer; the README one is not it.
    assert is_solution_commit("Time: 0 ms (100%), Space: 43.7 MB (6.92%) - LeetHub")
    assert not is_solution_commit("Create README - LeetHub")
    assert not is_solution_commit("Update README - Topic Tags")
    assert not is_solution_commit("Updated stats")


def test_the_folder_is_the_problem():
    assert slug_from_path("0876-middle-of-the-linked-list/0876-middle-of-the-linked-list.java") == "0876-middle-of-the-linked-list"
    assert slug_from_path("0584-find-customer-referee/0584-find-customer-referee.sql") == "0584-find-customer-referee"


def test_repo_level_files_are_not_problems():
    assert slug_from_path("README.md") is None
    assert slug_from_path("stats.json") is None


def test_a_solution_commit_becomes_one_event_per_folder():
    commits = [commit("a", "Time: 1 ms - LeetHub"), commit("b", "Update README - Topic Tags")]
    files = {"a": ["0876-middle-of-the-linked-list/0876-middle-of-the-linked-list.java"],
             "b": ["README.md"]}
    assert solve_events(commits, files) == [
        ("0876-middle-of-the-linked-list", datetime(2026, 8, 19, 6, 23)),
    ]


def test_solving_the_same_problem_twice_is_two_events():
    """The whole point: a repeat is practice, and it used to be invisible."""
    commits = [
        commit("a", "Time: 1 ms - LeetHub", "2026-08-10T10:00:00Z"),
        commit("b", "Time: 1 ms - LeetHub", "2026-08-19T06:23:00Z"),
    ]
    path = "0876-middle-of-the-linked-list/0876-middle-of-the-linked-list.java"
    events = solve_events(commits, {"a": [path], "b": [path]})
    assert [at.date().isoformat() for _, at in events] == ["2026-08-10", "2026-08-19"]


def test_a_commit_touching_a_folder_twice_counts_once():
    commits = [commit("a", "Time: 1 ms - LeetHub")]
    files = {"a": ["0001-two-sum/0001-two-sum.java", "0001-two-sum/README.md"]}
    assert len(solve_events(commits, files)) == 1
