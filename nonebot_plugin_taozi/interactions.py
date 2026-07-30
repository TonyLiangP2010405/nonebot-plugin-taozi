from __future__ import annotations

from .lexicon import normalize_term

ALLOWED_SELF_COLORS = ("白桃", "黑桃", "红桃", "黄桃")
_COLOR_INDEX = {normalize_term(color): color for color in ALLOWED_SELF_COLORS}
_CANCEL_WORDS = {"取消", "移除", "清除", "无"}


def parse_self_color(value: str) -> str | None:
    return _COLOR_INDEX.get(normalize_term(value))


def is_cancel_request(value: str) -> bool:
    return normalize_term(value) in _CANCEL_WORDS


def render_color_selected(color: str) -> str:
    lines = [
        f"已将你自选的桃色记录为：{color}。",
        "这是你主动选择的插件内玩笑身份，不代表机器人对你的评价。",
        "发送“/我的桃色 取消”可随时移除。",
    ]
    if color == "红桃":
        lines.append("提示：红桃的稳定社区含义目前仍未核实，这里只记录名称。")
    return "\n".join(lines)

