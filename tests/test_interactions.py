from nonebot_plugin_taozi.interactions import (
    is_cancel_request,
    parse_self_color,
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

