from datetime import datetime, timedelta

import pytest

from app.services.email_change_service import (
    CODE_LENGTH,
    CODE_TTL_MINUTES,
    MAX_ATTEMPTS,
    RESEND_COOLDOWN_SECONDS,
    EmailChangeError,
    check_usable,
    expiry_for,
    generate_code,
    normalise_email,
    notice_message,
    seconds_until_resend,
    validate_target,
    verification_message,
)

NOW = datetime(2026, 8, 5, 12, 0, 0)


class TestNormalise:
    def test_case_and_padding_are_removed(self):
        assert normalise_email("  Foo@Example.COM ") == "foo@example.com"

    def test_blank_is_rejected(self):
        with pytest.raises(EmailChangeError, match="Enter an email"):
            normalise_email("   ")


class TestValidateTarget:
    def test_the_current_address_is_rejected(self):
        with pytest.raises(EmailChangeError, match="already your email"):
            validate_target("me@example.com", "me@example.com", taken=False)

    def test_the_current_address_is_rejected_in_a_different_case(self):
        # Otherwise "ME@Example.com" looks like a change but resolves to the
        # same row, leaving a pointless request sitting in the table.
        with pytest.raises(EmailChangeError, match="already your email"):
            validate_target("  ME@Example.com ", "me@example.com", taken=False)

    def test_an_address_belonging_to_someone_else_is_rejected(self):
        with pytest.raises(EmailChangeError, match="cannot be used"):
            validate_target("taken@example.com", "me@example.com", taken=True)

    def test_the_refusal_does_not_confirm_the_account_exists(self):
        # A logged-in user must not be able to use this to test whether an
        # address is registered, so the message says nothing about why.
        with pytest.raises(EmailChangeError) as exc:
            validate_target("taken@example.com", "me@example.com", taken=True)

        assert "already" not in str(exc.value).lower()
        assert "exists" not in str(exc.value).lower()

    def test_a_valid_target_comes_back_normalised(self):
        assert (
            validate_target(" New@Example.com ", "me@example.com", taken=False)
            == "new@example.com"
        )


class TestCode:
    def test_a_code_is_six_digits(self):
        for _ in range(200):
            code = generate_code()
            assert len(code) == CODE_LENGTH
            assert code.isdigit()

    def test_low_numbers_keep_their_leading_zeros(self):
        # A code of "42" instead of "000042" would fail the six-digit pattern
        # on the way back in and lock the user out of their own request.
        assert all(len(generate_code()) == CODE_LENGTH for _ in range(500))

    def test_codes_are_not_all_the_same(self):
        assert len({generate_code() for _ in range(50)}) > 1

    def test_expiry_is_the_configured_window(self):
        assert expiry_for(NOW) == NOW + timedelta(minutes=CODE_TTL_MINUTES)


class TestCheckUsable:
    def test_a_fresh_unused_request_passes(self):
        check_usable(NOW + timedelta(minutes=5), attempts=0, consumed_at=None, now=NOW)

    def test_an_expired_request_is_rejected(self):
        with pytest.raises(EmailChangeError, match="expired"):
            check_usable(NOW, attempts=0, consumed_at=None, now=NOW)

    def test_expiry_is_inclusive_at_the_boundary(self):
        with pytest.raises(EmailChangeError, match="expired"):
            check_usable(NOW, attempts=0, consumed_at=None, now=NOW)

        check_usable(
            NOW + timedelta(seconds=1), attempts=0, consumed_at=None, now=NOW
        )

    def test_a_used_code_cannot_be_replayed(self):
        with pytest.raises(EmailChangeError, match="already been used"):
            check_usable(
                NOW + timedelta(minutes=5), attempts=0, consumed_at=NOW, now=NOW
            )

    def test_a_used_code_is_rejected_before_expiry_is_considered(self):
        # Both conditions hold; the reply should name the real one.
        with pytest.raises(EmailChangeError, match="already been used"):
            check_usable(NOW, attempts=0, consumed_at=NOW, now=NOW)

    def test_the_attempt_limit_stops_guessing(self):
        with pytest.raises(EmailChangeError, match="Too many"):
            check_usable(
                NOW + timedelta(minutes=5),
                attempts=MAX_ATTEMPTS,
                consumed_at=None,
                now=NOW,
            )

    def test_the_last_allowed_attempt_still_goes_through(self):
        check_usable(
            NOW + timedelta(minutes=5),
            attempts=MAX_ATTEMPTS - 1,
            consumed_at=None,
            now=NOW,
        )


class TestResendCooldown:
    def test_an_immediate_resend_has_to_wait_the_full_window(self):
        assert seconds_until_resend(NOW, NOW) == RESEND_COOLDOWN_SECONDS

    def test_the_wait_counts_down(self):
        assert seconds_until_resend(NOW, NOW + timedelta(seconds=20)) == (
            RESEND_COOLDOWN_SECONDS - 20
        )

    def test_zero_once_the_window_has_passed(self):
        later = NOW + timedelta(seconds=RESEND_COOLDOWN_SECONDS + 1)
        assert seconds_until_resend(NOW, later) == 0

    def test_a_clock_that_moved_backwards_never_returns_a_negative_wait(self):
        assert seconds_until_resend(NOW, NOW - timedelta(hours=1)) >= 0


class TestMessages:
    def test_the_code_appears_in_the_body(self):
        _, body = verification_message("123456", "Sruti")
        assert "123456" in body

    def test_the_name_is_used_when_there_is_one(self):
        _, body = verification_message("123456", "Sruti")
        assert body.startswith("Hi Sruti,")

    def test_a_missing_name_does_not_leave_a_dangling_greeting(self):
        _, body = verification_message("123456", None)
        assert body.startswith("Hi,")
        assert "None" not in body

    def test_the_body_says_how_long_the_code_lasts(self):
        _, body = verification_message("123456", None)
        assert f"{CODE_TTL_MINUTES} minutes" in body

    def test_the_body_tells_a_bystander_nothing_has_changed_yet(self):
        # Someone who did not request this needs to know they can ignore it.
        _, body = verification_message("123456", None)
        assert "did not" in body.lower()

    def test_the_notice_names_the_destination_address(self):
        _, body = notice_message("new@example.com", "Sruti")
        assert "new@example.com" in body

    def test_the_notice_carries_no_code(self):
        # It goes to the address being left behind; a code there would defeat
        # the point of proving control of the new one.
        code = "123456"
        _, body = notice_message("new@example.com", None)
        assert code not in body

    def test_the_notice_says_what_to_do_if_it_was_not_you(self):
        _, body = notice_message("new@example.com", None)
        assert "password" in body.lower()
