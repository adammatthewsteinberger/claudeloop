# Made with love by Vibey, the auto-vibecoding machine by Adam Matthew Steinberger.
from claudeloop.domain.capacity import (
    AuthenticationFailed,
    Available,
    CreditsExhausted,
    WindowExhausted,
    is_waitable,
)


def test_available_is_waitable_trivially_true():
    assert is_waitable(Available()) is True


def test_window_exhausted_is_waitable():
    assert is_waitable(WindowExhausted(rate_limit_type="five_hour")) is True


def test_credits_exhausted_is_waitable():
    assert is_waitable(CreditsExhausted()) is True


def test_authentication_failed_is_not_waitable():
    assert is_waitable(AuthenticationFailed(detail="bad key")) is False
