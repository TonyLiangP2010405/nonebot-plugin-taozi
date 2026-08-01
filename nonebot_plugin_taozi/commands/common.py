from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import nonebot_plugin_localstore as store
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.matcher import Matcher

from ..config import plugin_config
from ..fortune import Cooldown
from ..output import finish_message_card
from ..state import TaoziStateStore

state_store = TaoziStateStore(store.get_plugin_data_file("state.json"))
fun_cooldown = Cooldown(plugin_config.taozi_fun_cooldown_seconds)


def get_group_id(event: MessageEvent) -> str | None:
    if isinstance(event, GroupMessageEvent):
        return str(event.group_id)
    return None


def get_scope_id(event: MessageEvent) -> str:
    group_id = get_group_id(event)
    if group_id is not None:
        return f"group:{group_id}"
    return f"private:{event.get_user_id()}"


def get_today():
    try:
        timezone = ZoneInfo(plugin_config.taozi_timezone)
    except ZoneInfoNotFoundError:
        timezone = ZoneInfo("Asia/Shanghai")
    return datetime.now(timezone).date()


async def is_fun_enabled(event: MessageEvent) -> bool:
    if not plugin_config.taozi_fun_enabled:
        return False
    group_id = get_group_id(event)
    if group_id is None:
        return True
    return await state_store.is_group_enabled(group_id, default=True)


async def require_fun(
    matcher: type[Matcher],
    event: MessageEvent,
    *,
    command_key: str,
    apply_default_cooldown: bool = True,
) -> None:
    if not await is_fun_enabled(event):
        await finish_message_card(
            matcher,
            "桃趣互动已关闭",
            "本会话的桃趣互动已关闭；桃系词典仍可正常使用。",
            chips=("词典仍可用",),
        )

    if not apply_default_cooldown:
        return

    cooldown_key = f"{command_key}:{get_scope_id(event)}:{event.get_user_id()}"
    remaining = fun_cooldown.acquire(cooldown_key)
    if remaining > 0:
        await finish_message_card(
            matcher,
            "稍等一下",
            f"桃趣冷却中，请等待约 {remaining:.0f} 秒再试。",
            chips=("冷却中",),
        )
