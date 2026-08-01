from nonebot import on_fullmatch, on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.params import RegexStr
from nonebot.permission import SUPERUSER

from ..config import plugin_config
from ..output import finish_message_card
from .common import get_group_id, is_fun_enabled, state_store

fun_status = on_fullmatch("桃趣状态", priority=10, block=True)
fun_settings = on_regex(
    r"^桃趣(?:\s+(?P<action>.+?))?\s*$",
    permission=SUPERUSER | GROUP_ADMIN | GROUP_OWNER,
    priority=10,
    block=True,
)


@fun_status.handle()
async def handle_fun_status(event: MessageEvent) -> None:
    enabled = await is_fun_enabled(event)
    state = "开启" if enabled else "关闭"
    detail = ""
    if not plugin_config.taozi_fun_enabled:
        detail = "\n全局配置 TAOZI_FUN_ENABLED=false。"
    body = f"当前会话的桃趣互动：{state}。{detail}\n桃系词典不受此开关影响。"
    await finish_message_card(
        fun_status,
        "桃趣状态",
        body,
        chips=(state, "词典始终可用"),
    )


@fun_settings.handle()
async def handle_fun_settings(
    event: MessageEvent,
    action: str | None = RegexStr("action"),
) -> None:
    if not isinstance(event, GroupMessageEvent):
        await finish_message_card(
            fun_settings,
            "无法设置",
            "桃趣开关只能在群聊中设置。",
        )

    action = (action or "").strip()
    group_id = get_group_id(event)
    if group_id is None:
        await finish_message_card(
            fun_settings,
            "无法设置",
            "无法识别当前群聊。",
        )

    if action in {"开启", "打开", "启用"}:
        await state_store.set_group_enabled(group_id, True)
        if plugin_config.taozi_fun_enabled:
            await finish_message_card(
                fun_settings,
                "桃趣设置",
                "已开启本群的桃趣互动。",
                chips=("已开启",),
            )
        body = (
            "已保存本群的开启设置，但全局配置 TAOZI_FUN_ENABLED=false，"
            "修改配置并重启后才会生效。"
        )
        await finish_message_card(
            fun_settings,
            "设置已保存",
            body,
            chips=("等待全局开启",),
        )

    if action in {"关闭", "禁用"}:
        await state_store.set_group_enabled(group_id, False)
        await finish_message_card(
            fun_settings,
            "桃趣设置",
            "已关闭本群的桃趣互动；桃系词典仍可使用。",
            chips=("已关闭", "词典仍可用"),
        )

    if action == "状态":
        enabled = await is_fun_enabled(event)
        state = "开启" if enabled else "关闭"
        await finish_message_card(
            fun_settings,
            "桃趣状态",
            f"本群桃趣互动当前为：{state}。",
            chips=(state,),
        )

    await finish_message_card(
        fun_settings,
        "桃趣设置",
        "用法：桃趣 开启｜桃趣 关闭｜桃趣 状态",
        chips=("仅群管理可用",),
    )
