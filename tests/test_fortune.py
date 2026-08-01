from datetime import date, timedelta

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
    rendered = render_fortune(first, "测试桃", "10001", "黑桃")
    assert "测试桃的今日桃签" in rendered
    assert "账号：10001" in rendered
    assert "自选桃色：黑桃" in rendered
    assert "玩笑" in rendered
    assert "不是主播原话" in rendered


def test_daily_fortune_uses_the_date_in_each_draw() -> None:
    first_day = date(2026, 8, 1)
    results = [
        pick_daily_fortune("10001", first_day + timedelta(days=offset))
        for offset in range(len(FORTUNES))
    ]

    assert all(result in FORTUNES for result in results)
    assert len(set(results)) > 1


def test_every_user_is_stable_until_calendar_day_changes() -> None:
    day = date(2026, 8, 1)
    user_ids = ("1", "10001", "987654321", "anonymous-user")
    today_results = {}
    for user_id in user_ids:
        today = pick_daily_fortune(user_id, day)
        assert pick_daily_fortune(user_id, day) == today
        today_results[user_id] = today

    tomorrow_results = {
        user_id: pick_daily_fortune(user_id, day + timedelta(days=1))
        for user_id in user_ids
    }
    assert any(tomorrow_results[user_id] != today_results[user_id] for user_id in user_ids)


def test_fortune_pool_has_enough_unique_options() -> None:
    assert len(FORTUNES) >= 96
    assert len({fortune.name for fortune in FORTUNES}) == len(FORTUNES)
    assert len({fortune.message for fortune in FORTUNES}) == len(FORTUNES)


def test_cooldown_reports_remaining_seconds() -> None:
    cooldown = Cooldown(8)
    assert cooldown.acquire("user:command", now=10.0) == 0
    assert cooldown.acquire("user:command", now=13.0) == 5.0
    assert cooldown.acquire("user:command", now=18.0) == 0
