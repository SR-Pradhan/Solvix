from app.clients.leetcode_client import slug_from_folder, tag_slug
from app.services.problem_service import problem_url


def test_tag_slug_lowercases_and_hyphenates():
    assert tag_slug("Binary Search") == "binary-search"
    assert tag_slug("Hash Table") == "hash-table"


def test_tag_slug_handles_multiword_tags():
    assert tag_slug("Divide and Conquer") == "divide-and-conquer"
    assert tag_slug("Dynamic Programming") == "dynamic-programming"


def test_tag_slug_strips_punctuation():
    assert tag_slug("Depth-First Search") == "depth-first-search"
    assert tag_slug("Doubly-Linked List") == "doubly-linked-list"


def test_tag_slug_of_an_already_slugged_tag_is_unchanged():
    assert tag_slug("binary-search") == "binary-search"


def test_tag_slug_of_junk_is_empty_rather_than_a_bad_query():
    assert tag_slug("   ") == ""
    assert tag_slug("!!!") == ""


def test_slug_from_folder_drops_the_leading_number():
    assert slug_from_folder("0001-two-sum") == "two-sum"
    assert slug_from_folder("1295-find-numbers-with-even-number-of-digits") == (
        "find-numbers-with-even-number-of-digits"
    )


def test_slug_from_folder_leaves_an_unnumbered_slug_alone():
    assert slug_from_folder("two-sum") == "two-sum"


def test_slug_from_folder_keeps_digits_inside_the_title():
    # "3sum" is part of the name, not a leading problem number.
    assert slug_from_folder("0015-3sum") == "3sum"


def test_slug_from_folder_trims_whitespace():
    assert slug_from_folder("  0001-two-sum  ") == "two-sum"


def test_problem_url_builds_a_leetcode_link_from_a_folder():
    assert (
        problem_url("leetcode", "0001-two-sum")
        == "https://leetcode.com/problems/two-sum/"
    )


def test_problem_url_splits_a_codeforces_id_into_contest_and_index():
    assert (
        problem_url("codeforces", "1234A")
        == "https://codeforces.com/problemset/problem/1234/A"
    )


def test_problem_url_handles_multi_character_codeforces_indexes():
    # Division-split problems use indexes like E2, so the split is
    # digits-then-rest rather than a fixed length.
    assert (
        problem_url("codeforces", "2249E2")
        == "https://codeforces.com/problemset/problem/2249/E2"
    )


def test_problem_url_returns_none_for_an_unparseable_codeforces_id():
    assert problem_url("codeforces", "not-an-id") is None
