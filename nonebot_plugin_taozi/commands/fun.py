import secrets
from math import ceil

from nonebot import on_fullmatch, on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.params import RegexStr

from ..config import plugin_config
from ..fortune import Cooldown, pick_daily_fortune, render_fortune
from ..interactions import (
    ALLOWED_SELF_COLORS,
    is_cancel_request,
    parse_self_color,
    render_color_distribution,
    render_color_selected,
)
from ..lexicon import BUILTIN_LEXICON, render_entry
from ..output import finish_fortune_card, finish_lexicon_card, finish_message_card
from .common import get_scope_id, get_today, require_fun, state_store

daily_fortune = on_fullmatch(
    ("今日桃签", "桃签"),
    priority=10,
    block=True,
)
random_term = on_fullmatch(
    ("随机桃词", "随机桃梗"),
    priority=10,
    block=True,
)
self_color = on_regex(
    r"^(?:我的桃色|我是桃)(?:\s+(?P<color>.+?))?\s*$",
    priority=10,
    block=True,
)
cancel_color = on_fullmatch("取消桃色", priority=10, block=True)
color_chart = on_fullmatch(
    ("群桃图鉴", "桃色图鉴"),
    priority=10,
    block=True,
)
random_term_notice_cooldown = Cooldown(60)


def get_fortune_owner_name(event: MessageEvent) -> str:
    raw_name = event.sender.card or event.sender.nickname or "用户"
    normalized = " ".join(raw_name.split()) or "用户"
    return f"{normalized[:13]}…" if len(normalized) > 14 else normalized


@daily_fortune.handle()
async def handle_daily_fortune(event: MessageEvent) -> None:
    await require_fun(daily_fortune, event, command_key="daily_fortune")
    day = get_today()
    owner_id = event.get_user_id()
    owner_name = get_fortune_owner_name(event)
    selected_color = await state_store.get_self_color(get_scope_id(event), owner_id)
    fortune = pick_daily_fortune(owner_id, day)
    await finish_fortune_card(
        daily_fortune,
        fortune,
        day.isoformat(),
        owner_name,
        owner_id,
        selected_color,
        render_fortune(fortune, owner_name, owner_id, selected_color),
    )


@random_term.handle()
async def handle_random_term(event: MessageEvent) -> None:
    await require_fun(
        random_term,
        event,
        command_key="random_term",
        apply_default_cooldown=False,
    )
    cooldown_key = f"{get_scope_id(event)}:{event.get_user_id()}"
    remaining = await state_store.acquire_random_term(
        get_scope_id(event),
        event.get_user_id(),
        plugin_config.taozi_random_term_cooldown_seconds,
    )
    if remaining > 0:
        if random_term_notice_cooldown.acquire(cooldown_key) > 0:
            await random_term.finish()
        await finish_message_card(
            random_term,
            "随机桃词冷却中",
            f"每位群友每小时可抽取一次，还需等待约 {max(1, ceil(remaining / 60))} 分钟。",
            chips=("防刷屏", "每群单独计算"),
        )

    entry = secrets.choice(BUILTIN_LEXICON.entries)
    await finish_lexicon_card(
        random_term,
        entry,
        render_entry(
            entry,
            show_sources=plugin_config.taozi_lexicon_show_sources,
            compact=True,
        ),
        compact=True,
    )


@self_color.handle()
async def handle_self_color(
    event: MessageEvent,
    value: str | None = RegexStr("color"),
) -> None:
    await require_fun(self_color, event, command_key="self_color")
    value = (value or "").strip()
    scope_id = get_scope_id(event)
    user_id = event.get_user_id()

    if not value:
        selected = await state_store.get_self_color(scope_id, user_id)
        if selected is None:
            body = (
                "你还没有自选桃色。\n"
                f"可选：{'、'.join(ALLOWED_SELF_COLORS)}\n"
                "用法：我的桃色 黑桃"
            )
            await finish_message_card(
                self_color,
                "我的桃色",
                body,
                chips=("自愿选择", "随时取消"),
            )
        body = (
            f"你当前自选的桃色是：{selected}。\n"
            "这是插件内的自愿玩笑身份，不代表机器人评价。"
        )
        await finish_message_card(
            self_color,
            "我的桃色",
            body,
            chips=(selected or "未选择", "自愿选择"),
        )

    if is_cancel_request(value):
        removed = await state_store.remove_self_color(scope_id, user_id)
        message = "已取消你的自选桃色。" if removed else "你目前没有自选桃色。"
        await finish_message_card(
            self_color,
            "桃色设置",
            message,
            chips=("已更新",),
        )

    color = parse_self_color(value)
    if color is None:
        body = (
            f"不支持“{value}”。可选桃色：{'、'.join(ALLOWED_SELF_COLORS)}；"
            "也可以发送“我的桃色 取消”。"
        )
        await finish_message_card(
            self_color,
            "无法识别桃色",
            body,
            chips=("请重新选择",),
        )

    await state_store.set_self_color(scope_id, user_id, color)
    await finish_message_card(
        self_color,
        "桃色设置成功",
        render_color_selected(color),
        chips=(color, "自愿选择"),
        footer="这只是插件内的玩笑身份；发送“我的桃色 取消”即可移除。",
    )


@cancel_color.handle()
async def handle_cancel_color(event: MessageEvent) -> None:
    await require_fun(cancel_color, event, command_key="cancel_color")
    removed = await state_store.remove_self_color(get_scope_id(event), event.get_user_id())
    message = "已取消你的自选桃色。" if removed else "你目前没有自选桃色。"
    await finish_message_card(
        cancel_color,
        "桃色设置",
        message,
        chips=("已更新",),
    )


@color_chart.handle()
async def handle_color_chart(event: MessageEvent) -> None:
    if not isinstance(event, GroupMessageEvent):
        await finish_message_card(
            color_chart,
            "仅限群聊",
            "群桃图鉴只统计当前群聊，私聊中无法查看。",
            chips=("不公开名单",),
        )

    await require_fun(color_chart, event, command_key="color_chart")
    counts = await state_store.get_self_color_counts(get_scope_id(event))
    body, total = render_color_distribution(counts)
    await finish_message_card(
        color_chart,
        "群桃图鉴",
        body,
        chips=(f"已选择 {total} 人", "仅统计人数"),
        footer="桃色均由群友本人主动选择；插件不会自动判断或公开名单。",
    )
