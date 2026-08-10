from datetime import datetime

from app.services.ingestion_service import choose_fetch_start

SOLVED_AT = datetime(2026, 6, 28, 15, 30, 51)
SOLVED_AT_EPOCH = 1782660651


def test_first_ever_sync_fetches_everything():
    assert choose_fetch_start(full_import_done=False, latest_solved_at=None) is None


def test_resumes_once_a_full_import_finished():
    assert (
        choose_fetch_start(full_import_done=True, latest_solved_at=SOLVED_AT)
        == SOLVED_AT_EPOCH
    )


def test_interrupted_import_starts_over_despite_stored_rows():
    # The bug this exists for: an import that stopped after one recent
    # submission left a row behind, and resuming from it declared the whole
    # older history already imported.
    assert (
        choose_fetch_start(full_import_done=False, latest_solved_at=SOLVED_AT) is None
    )


def test_completed_import_with_no_rows_still_fetches_everything():
    # An account whose history was genuinely empty when it was imported: there
    # is no point to resume from, so start at the beginning.
    assert choose_fetch_start(full_import_done=True, latest_solved_at=None) is None


def test_boundary_is_the_stored_timestamp_itself():
    # Codeforces excludes the boundary, and the stored submission is already
    # saved, so passing its own timestamp is correct rather than off by one.
    assert (
        choose_fetch_start(True, datetime(2026, 1, 1, 0, 0, 0)) == 1767225600
    )
