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
