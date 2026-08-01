from nonebot_plugin_taozi.interactions import (
    get_color_fortune_note,
    is_cancel_request,
    parse_self_color,
    render_color_distribution,
    render_color_selected,
)


def test_self_color_is_explicit_and_limited() -> None:
    assert parse_self_color(" 黑桃 ") == "黑桃"
    assert parse_self_color("蓝桃") is None
    assert is_cancel_request("取消")


def test_red_color_keeps_unknown_meaning_warning() -> None:
    rendered = render_color_selected("红桃")
    assert "主动选择" in rendered
    assert "稳定社区含义目前仍未核实" in rendered


def test_each_color_has_a_safe_fortune_note() -> None:
    assert "支持" in (get_color_fortune_note("白桃") or "")
    assert "玩笑" in (get_color_fortune_note("黑桃") or "")
    assert "待考证" in (get_color_fortune_note("红桃") or "")
    assert "喜欢" in (get_color_fortune_note("黄桃") or "")
    assert get_color_fortune_note(None) is None


def test_color_distribution_only_contains_counts() -> None:
    body, total = render_color_distribution({"白桃": 1, "黑桃": 2})

    assert total == 3
    assert "白桃：1 人" in body
    assert "黑桃：2 人" in body
    assert "红桃：0 人" in body
    assert "不公开账号或昵称" in body
