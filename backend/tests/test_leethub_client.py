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
