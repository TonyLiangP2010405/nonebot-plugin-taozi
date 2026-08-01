from __future__ import annotations

from collections.abc import Mapping

from .lexicon import normalize_term

ALLOWED_SELF_COLORS = ("白桃", "黑桃", "红桃", "黄桃")
_COLOR_INDEX = {normalize_term(color): color for color in ALLOWED_SELF_COLORS}
_CANCEL_WORDS = {"取消", "移除", "清除", "无"}
_FORTUNE_NOTES = {
    "白桃": "把支持和好心情分一点给身边的人。",
    "黑桃": "今天可以皮一下，但要把玩笑留在彼此舒服的边界内。",
    "红桃": "红桃含义仍待考证，今天先把它当作你主动选择的身份纪念。",
    "黄桃": "遇到喜欢的角色或事物，可以放心表达欣赏。",
}


def parse_self_color(value: str) -> str | None:
    return _COLOR_INDEX.get(normalize_term(value))


def is_cancel_request(value: str) -> bool:
    return normalize_term(value) in _CANCEL_WORDS


def get_color_fortune_note(color: str | None) -> str | None:
    return _FORTUNE_NOTES.get(color or "")


def render_color_distribution(counts: Mapping[str, int]) -> tuple[str, int]:
    normalized = {color: max(0, counts.get(color, 0)) for color in ALLOWED_SELF_COLORS}
    total = sum(normalized.values())
    lines = [f"{color}：{normalized[color]} 人" for color in ALLOWED_SELF_COLORS]
    if total:
        intro = f"本群共有 {total} 位群友主动选择了桃色。"
    else:
        intro = "本群还没有群友选择桃色。发送“我的桃色 黑桃”等指令即可加入。"
    body = "\n".join(
        [
            intro,
            "",
            *lines,
            "",
            "图鉴只显示人数，不公开账号或昵称。",
        ]
    )
    return body, total


def render_color_selected(color: str) -> str:
    lines = [
        f"已将你自选的桃色记录为：{color}。",
        "这是你主动选择的插件内玩笑身份，不代表机器人对你的评价。",
        "发送“我的桃色 取消”可随时移除。",
    ]
    if color == "红桃":
        lines.append("提示：红桃的稳定社区含义目前仍未核实，这里只记录名称。")
    return "\n".join(lines)
