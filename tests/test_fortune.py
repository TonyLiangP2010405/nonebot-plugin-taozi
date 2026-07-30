from datetime import date

from nonebot_plugin_taozi.fortune import (
    FORTUNES,
    Cooldown,
    pick_daily_fortune,
    render_fortune,
)


def test_daily_fortune_is_stable_for_same_user_and_day() -> None:
    day = date(2026, 7, 30)
    first = pick_daily_fortune("10001", day)
    second = pick_daily_fortune("10001", day)
    assert first == second
    assert "不是主播原话" in render_fortune(first)


def test_daily_fortune_changes_input_by_day() -> None:
    first = pick_daily_fortune("10001", date(2026, 7, 30))
    second = pick_daily_fortune("10001", date(2026, 7, 31))
    assert first in FORTUNES
    assert second in FORTUNES


def test_cooldown_reports_remaining_seconds() -> None:
    cooldown = Cooldown(8)
    assert cooldown.acquire("user:command", now=10.0) == 0
    assert cooldown.acquire("user:command", now=13.0) == 5.0
    assert cooldown.acquire("user:command", now=18.0) == 0
