import secrets

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.params import CommandArg

from ..config import plugin_config
from ..fortune import pick_daily_fortune, render_fortune
from ..interactions import (
    ALLOWED_SELF_COLORS,
    is_cancel_request,
    parse_self_color,
    render_color_selected,
)
from ..lexicon import BUILTIN_LEXICON, render_entry
from ..output import finish_fortune_card, finish_lexicon_card, finish_message_card
from .common import get_scope_id, get_today, require_fun, state_store

daily_fortune = on_command(
    "今日桃签",
    aliases={"桃签"},
    priority=10,
    block=True,
)
random_term = on_command(
    "随机桃词",
    aliases={"随机桃梗"},
    priority=10,
    block=True,
)
self_color = on_command(
    "我的桃色",
    aliases={"我是桃"},
    priority=10,
    block=True,
)
cancel_color = on_command("取消桃色", priority=10, block=True)


@daily_fortune.handle()
async def handle_daily_fortune(event: MessageEvent) -> None:
    await require_fun(daily_fortune, event, command_key="daily_fortune")
    day = get_today()
    fortune = pick_daily_fortune(event.get_user_id(), day)
    await finish_fortune_card(
        daily_fortune,
        fortune,
        day.isoformat(),
        render_fortune(fortune),
    )


@random_term.handle()
async def handle_random_term(event: MessageEvent) -> None:
    await require_fun(random_term, event, command_key="random_term")
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
async def handle_self_color(event: MessageEvent, args: Message = CommandArg()) -> None:
    await require_fun(self_color, event, command_key="self_color")
    value = args.extract_plain_text().strip()
    scope_id = get_scope_id(event)
    user_id = event.get_user_id()

    if not value:
        selected = await state_store.get_self_color(scope_id, user_id)
        if selected is None:
            body = (
                "你还没有自选桃色。\n"
                f"可选：{'、'.join(ALLOWED_SELF_COLORS)}\n"
                "用法：/我的桃色 黑桃"
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
            "也可以发送“/我的桃色 取消”。"
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
        footer="这只是插件内的玩笑身份；发送“/我的桃色 取消”即可移除。",
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
