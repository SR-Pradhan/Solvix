"""Tests written from real solutions in a real LeetHub repo.

Every "not flagged" case below is a false positive this feature actually
produced during development, on genuine code. They are the point of the file:
the naive version of this idea accuses correct solutions, and the cost of
that is not symmetrical — a missed brute force loses an insight, a wrongly
accused optimal solution teaches the reader to distrust the card.
"""

from app.services.approach_service import (
    has_nested_loops,
    language_of,
    review,
    strip_noise,
    techniques_in,
)

JAVA = "java"


def verdict(tags, code, language=JAVA):
    return review(tags, code, language)["verdict"]


# --- reading the source ----------------------------------------------------

def test_language_comes_from_the_file_extension():
    assert language_of("0001-two-sum.java") == JAVA
    assert language_of("0001-two-sum.py") == "python"
    assert language_of("0001-two-sum.cpp") is None


def test_a_technique_named_in_a_comment_is_not_a_technique_used():
    code = "// could use a HashMap here\nint x = 0;"
    assert techniques_in(code, JAVA) == set()


def test_a_technique_named_in_a_string_is_not_one_either():
    assert techniques_in('String s = "PriorityQueue";', JAVA) == set()


def test_comments_are_stripped_but_code_survives():
    assert "HashMap" in strip_noise("HashMap<Integer,Integer> m; // a map")


# --- nested loops, the brute-force tell ------------------------------------

def test_sequential_loops_are_not_nested():
    """Three loops in a row is trapping-rain-water, and it is O(n).

    The first version popped its loop stack before decrementing the brace
    depth, so a finished loop stayed on the stack and the next one looked
    nested. It accused an optimal solution.
    """
    code = """
    for (int i = 1; i < n; i++) { leftMax[i] = 1; }
    for (int i = n - 2; i >= 0; i--) { rightMax[i] = 1; }
    for (int i = 0; i < n; i++) { total += 1; }
    """
    assert has_nested_loops(code, JAVA) is False


def test_a_loop_inside_a_loop_is_nested():
    code = "for (int i=0;i<n;i++) { for (int j=0;j<n;j++) { c++; } }"
    assert has_nested_loops(code, JAVA) is True


def test_python_nesting_is_read_from_indentation():
    assert has_nested_loops("for i in a:\n    for j in b:\n        c += 1\n", "python")
    assert not has_nested_loops("for i in a:\n    c += 1\nfor j in b:\n    c += 1\n", "python")


# --- the two conditions ----------------------------------------------------

def test_a_nested_loop_with_none_of_the_tagged_techniques_is_brute_force():
    """next-greater-element-i: tagged Monotonic Stack, solved with three loops."""
    code = """
    for (int i=0;i<n;i++) { for (int j=0;j<m;j++) { for (int k=j+1;k<m;k++) { x++; } } }
    """
    assert verdict(["Hash Table", "Stack", "Monotonic Stack"], code) == "Brute forced"


def test_using_any_one_of_the_tagged_techniques_is_enough():
    # A problem tagged four ways can legitimately be solved any of the four.
    code = "Arrays.sort(nums); for (int i=0;i<n;i++) { for(int j=0;j<n;j++){x++;} }"
    assert verdict(["Hash Table", "Sorting", "Stack"], code) == "As intended"


def test_a_single_pass_is_never_accused():
    """majority-element: Boyer-Moore, better than all three tags, none present."""
    code = "for (int i=0;i<n;i++){ if(cm==0) maj=nums[i]; cm++; }"
    assert verdict(["Sorting", "Hash Table", "Counting"], code) == "Not judged"


def test_a_frequency_array_counts_as_a_hash_table():
    """valid-anagram: int[26] is a hash table with the hashing inlined."""
    code = "int[] freq = new int[26]; for(int i=0;i<n;i++){ freq[s.charAt(i)-'a']++; }"
    assert verdict(["Hash Table", "Sorting"], code) == "As intended"


def test_a_counting_array_with_nested_subscripts_counts_too():
    """detect-squares: `count[point[0]][point[1]]++` is a direct-address table."""
    code = "int[][] count = new int[1001][1001]; void add(int[] p){ count[p[0]][p[1]]++; }"
    assert "Hash Table" in techniques_in(code, JAVA)


def test_a_string_builder_driven_from_its_end_is_a_stack():
    """remove-k-digits: an optimal monotonic stack, without the word Stack."""
    code = """
    StringBuilder sb = new StringBuilder();
    for (char d : num.toCharArray()) {
        while (k > 0 && sb.length() > 0 && sb.charAt(sb.length()-1) > d) {
            sb.deleteCharAt(sb.length()-1); k--;
        }
        sb.append(d);
    }
    """
    assert verdict(["Stack", "Monotonic Stack"], code) == "As intended"


def test_a_sliding_window_is_not_accused_of_brute_force():
    """minimum-size-subarray-sum: O(n), and textually a loop inside a loop.

    A sliding window and a two-pointer sweep are both `for` with an inner
    `while`, which the nesting test cannot tell from a brute force. When the
    problem is tagged that way the verdict is withheld.
    """
    code = """
    for (int r=0;r<n;r++){ sum += nums[r];
        while (sum >= target) { minLen = Math.min(minLen, r-l+1); sum -= nums[l]; l++; }
    }
    """
    assert verdict(["Binary Search", "Sliding Window"], code) != "Brute forced"


def test_two_pointers_earns_the_same_benefit_of_the_doubt():
    code = "for(int i=0;i<n;i++){ while(l<r){ l++; } }"
    assert verdict(["Dynamic Programming", "Two Pointers"], code) != "Brute forced"


# --- when it should say nothing --------------------------------------------

def test_a_problem_with_no_checkable_tag_gets_no_verdict():
    """"Greedy" and "Array" describe how you thought, not what you typed."""
    assert verdict(["Greedy", "Array", "Math"], "for(int i=0;i<n;i++){x++;}") == "Not judged"


def test_no_tags_at_all_is_not_a_verdict():
    assert verdict([], "for(int i=0;i<n;i++){for(int j=0;j<n;j++){x++;}}") == "Not judged"


def test_leetcodes_own_spelling_of_union_find_is_matched():
    # The tag is hyphenated; an un-hyphenated key silently matched nothing and
    # dropped every Union-Find problem from consideration.
    out = review(["Union-Find"], "int[] parent = new int[n];", JAVA)
    assert out["checkable"] == ["Union-Find"]
