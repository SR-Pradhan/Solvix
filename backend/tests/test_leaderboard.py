from types import SimpleNamespace

from app.services.leaderboard_service import display_name_for, rank


def entry(name, solved, days=1, you=False):
    return {"name": name, "solved": solved, "active_days": days, "is_you": you}


def user(display_name=None, handle=None, email="someone@example.com"):
    return SimpleNamespace(
        display_name=display_name, codeforces_handle=handle, email=email
    )


# --- what one account may see of another ---


def test_the_display_name_is_used_when_set():
    assert display_name_for(user(display_name="SR")) == "SR"


def test_a_blank_display_name_does_not_win():
    assert display_name_for(user(display_name="   ", handle="SR_Pradhan")) == "@SR_Pradhan"


def test_the_handle_stands_in_when_there_is_no_name():
    # Already public on Codeforces, so showing it reveals nothing new.
    assert display_name_for(user(handle="tourist")) == "@tourist"


def test_an_account_with_neither_is_anonymous_rather_than_emailed():
    # The important one: a leaderboard is the only screen where one account's
    # data is shown to another, and an email must never cross that line.
    shown = display_name_for(user(email="private@example.com"))
    assert shown == "Anonymous"
    assert "@example.com" not in shown


# --- ordering ---


def test_more_problems_places_higher():
    board = rank([entry("A", 3), entry("B", 9)])
    assert [e["name"] for e in board] == ["B", "A"]


def test_a_tie_on_volume_breaks_on_consistency():
    # Six problems over four days beats six in one sitting: the whole argument
    # of the app is that regular practice beats bursts.
    board = rank([entry("Burst", 6, days=1), entry("Steady", 6, days=4)])
    assert [e["name"] for e in board] == ["Steady", "Burst"]


def test_a_genuine_tie_shares_a_place():
    # Standard competition ranking. Numbering them 2nd and 3rd would invent a
    # difference the data does not contain.
    board = rank([entry("A", 6, days=2), entry("B", 6, days=2), entry("C", 1)])
    places = {e["name"]: e["place"] for e in board}
    assert places["A"] == places["B"] == 1
    assert places["C"] == 3


def test_the_leader_is_first_place():
    board = rank([entry("A", 2), entry("B", 5)])
    assert board[0]["place"] == 1


def test_order_is_stable_for_identical_rows():
    # Without the name as a final key the order would depend on however the
    # rows came back from the database, so the board could reshuffle between
    # two identical requests.
    first = rank([entry("Zoe", 4, days=2), entry("Adam", 4, days=2)])
    second = rank([entry("Adam", 4, days=2), entry("Zoe", 4, days=2)])
    assert [e["name"] for e in first] == [e["name"] for e in second] == ["Adam", "Zoe"]


def test_an_empty_week_ranks_nobody():
    assert rank([]) == []


def test_you_are_marked_without_changing_the_order():
    board = rank([entry("A", 9), entry("Me", 3, you=True)])
    assert [e["name"] for e in board] == ["A", "Me"]
    assert board[1]["is_you"] is True
