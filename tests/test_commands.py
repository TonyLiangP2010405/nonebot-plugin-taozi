from pathlib import Path
from time import time

import nonebot
import pytest
from nonebot.adapters.onebot.v11 import (
    Adapter,
    Bot,
    GroupMessageEvent,
    Message,
    MessageSegment,
)
from nonebot.adapters.onebot.v11.event import Sender
from nonebug import App

from nonebot_plugin_taozi import output
from nonebot_plugin_taozi.commands import settings
from nonebot_plugin_taozi.commands.lexicon import lexicon_command
from nonebot_plugin_taozi.lexicon import BUILTIN_LEXICON, render_entry
from nonebot_plugin_taozi.render import render_lexicon_card, render_message_card
from nonebot_plugin_taozi.state import TaoziStateStore


def make_group_event(message: str, *, role: str = "member") -> GroupMessageEvent:
    parsed = Message(message)
    return GroupMessageEvent(
        time=int(time()),
        self_id=10000,
        post_type="message",
        sub_type="normal",
        user_id=10001,
        message_type="group",
        message_id=1,
        message=parsed,
        original_message=parsed,
        raw_message=message,
        font=0,
        sender=Sender(user_id=10001, nickname="tester", role=role),
        to_me=True,
        group_id=20001,
    )


def create_onebot(app_context):
    adapter = nonebot.get_adapter(Adapter)
    return app_context.create_bot(base=Bot, adapter=adapter, self_id="10000")


@pytest.mark.asyncio
async def test_lexicon_command_with_term(app: App) -> None:
    entry = BUILTIN_LEXICON.find("黑桃")
    assert entry is not None
    expected = MessageSegment.image(
        await render_lexicon_card(entry, show_sources=True),
    )

    async with app.test_matcher(lexicon_command) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("/桃系词典 黑桃")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_lexicon_command_without_term_lists_entries(app: App) -> None:
    body = (
        "已收录桃系词条：\n"
        f"{BUILTIN_LEXICON.list_terms()}\n\n"
        "用法：/桃系词典 黑桃"
    )
    expected = MessageSegment.image(
        await render_message_card(
            "桃系词典",
            body,
            chips=("有出处", "可修订"),
            footer="输入“/桃系词典 词条名”查看解释、边界和来源。",
        )
    )

    async with app.test_matcher(lexicon_command) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("/桃系词典")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_lexicon_command_falls_back_to_text_when_render_fails(
    app: App,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fail_render(*args, **kwargs) -> bytes:
        raise RuntimeError("test render failure")

    monkeypatch.setattr(output, "render_lexicon_card", fail_render)
    entry = BUILTIN_LEXICON.find("黑桃")
    assert entry is not None
    expected = render_entry(entry)

    async with app.test_matcher(lexicon_command) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("/桃系词典 黑桃")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_fun_settings_rejects_group_member(app: App) -> None:
    async with app.test_matcher(settings.fun_settings) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("/桃趣 关闭", role="member")
        ctx.receive_event(bot, event)
        ctx.should_pass_rule()
        ctx.should_not_pass_permission()


@pytest.mark.asyncio
async def test_group_admin_can_disable_fun(
    app: App,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = TaoziStateStore(tmp_path / "state.json")
    monkeypatch.setattr(settings, "state_store", store)
    expected = MessageSegment.image(
        await render_message_card(
            "桃趣设置",
            "已关闭本群的桃趣互动；桃系词典仍可使用。",
            chips=("已关闭", "词典仍可用"),
        )
    )

    async with app.test_matcher(settings.fun_settings) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("/桃趣 关闭", role="admin")
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            expected,
            result=None,
            bot=bot,
        )
        ctx.should_finished()

    assert not await store.is_group_enabled("20001", default=True)
