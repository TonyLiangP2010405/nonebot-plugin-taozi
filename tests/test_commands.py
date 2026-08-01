from datetime import date
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
    PrivateMessageEvent,
)
from nonebot.adapters.onebot.v11.event import Sender
from nonebug import App

from nonebot_plugin_taozi import output
from nonebot_plugin_taozi.commands import fun, help, settings
from nonebot_plugin_taozi.commands.lexicon import lexicon_command
from nonebot_plugin_taozi.fortune import Cooldown, pick_daily_fortune
from nonebot_plugin_taozi.interactions import render_color_distribution, render_color_selected
from nonebot_plugin_taozi.lexicon import BUILTIN_LEXICON, render_entry
from nonebot_plugin_taozi.render import (
    render_fortune_card,
    render_lexicon_card,
    render_message_card,
)
from nonebot_plugin_taozi.state import TaoziStateStore


def make_group_event(
    message: str,
    *,
    role: str = "member",
    nickname: str = "tester",
    card: str | None = None,
) -> GroupMessageEvent:
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
        sender=Sender(
            user_id=10001,
            nickname=nickname,
            card=card,
            role=role,
        ),
        to_me=True,
        group_id=20001,
    )


def make_private_event(message: str) -> PrivateMessageEvent:
    parsed = Message(message)
    return PrivateMessageEvent(
        time=int(time()),
        self_id=10000,
        post_type="message",
        sub_type="friend",
        user_id=10001,
        message_type="private",
        message_id=1,
        message=parsed,
        original_message=parsed,
        raw_message=message,
        font=0,
        sender=Sender(user_id=10001, nickname="tester"),
        to_me=True,
    )


def create_onebot(app_context):
    adapter = nonebot.get_adapter(Adapter)
    return app_context.create_bot(base=Bot, adapter=adapter, self_id="10000")


@pytest.mark.asyncio
async def test_every_command_matches_plain_text_without_slash() -> None:
    adapter = nonebot.get_adapter(Adapter)
    bot = Bot(adapter=adapter, self_id="10000")

    examples = (
        (help.help_command, "桃纸帮助"),
        (lexicon_command, "桃系词典 黑桃"),
        (fun.random_term, "随机桃词"),
        (fun.daily_fortune, "今日桃签"),
        (fun.self_color, "我的桃色 黑桃"),
        (fun.cancel_color, "取消桃色"),
        (fun.color_chart, "群桃图鉴"),
        (settings.fun_status, "桃趣状态"),
        (settings.fun_settings, "桃趣 关闭"),
        (help.help_command, "桃纸助手"),
        (lexicon_command, "桃词典 白桃"),
        (fun.random_term, "随机桃梗"),
        (fun.daily_fortune, "桃签"),
        (fun.self_color, "我是桃 黄桃"),
        (fun.color_chart, "桃色图鉴"),
    )

    for matcher, message in examples:
        assert await matcher.check_rule(bot, make_group_event(message), {})


@pytest.mark.asyncio
async def test_commands_do_not_accept_slash_prefix() -> None:
    adapter = nonebot.get_adapter(Adapter)
    bot = Bot(adapter=adapter, self_id="10000")

    examples = (
        (help.help_command, "/桃纸帮助"),
        (lexicon_command, "/桃系词典 黑桃"),
        (fun.random_term, "/随机桃词"),
        (fun.daily_fortune, "/今日桃签"),
        (fun.self_color, "/我的桃色 黑桃"),
        (fun.cancel_color, "/取消桃色"),
        (fun.color_chart, "/群桃图鉴"),
        (settings.fun_status, "/桃趣状态"),
        (settings.fun_settings, "/桃趣 关闭"),
    )

    for matcher, message in examples:
        assert not await matcher.check_rule(bot, make_group_event(message), {})


@pytest.mark.asyncio
async def test_commands_require_full_text_boundary() -> None:
    adapter = nonebot.get_adapter(Adapter)
    bot = Bot(adapter=adapter, self_id="10000")

    examples = (
        (help.help_command, "请发桃纸帮助"),
        (lexicon_command, "我想看桃系词典 黑桃"),
        (fun.random_term, "来个随机桃词吧"),
        (fun.daily_fortune, "帮我抽今日桃签"),
        (fun.self_color, "看看我的桃色 黑桃"),
        (fun.cancel_color, "帮我取消桃色"),
        (fun.color_chart, "看看群桃图鉴"),
        (settings.fun_status, "看看桃趣状态"),
        (settings.fun_settings, "请把桃趣 关闭"),
    )

    for matcher, message in examples:
        assert not await matcher.check_rule(bot, make_group_event(message), {})


def test_daily_fortune_owner_prefers_group_card_and_limits_length() -> None:
    event = make_group_event(
        "今日桃签",
        nickname="昵称桃",
        card="  很长很长很长很长很长很长很长很长的群名片  ",
    )

    assert fun.get_fortune_owner_name(event) == "很长很长很长很长很长很长很…"


@pytest.mark.asyncio
async def test_daily_fortune_card_identifies_owner(
    app: App,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def allow_fun(*args, **kwargs) -> None:
        return None

    fixed_day = date(2026, 7, 31)
    store = TaoziStateStore(tmp_path / "state.json")
    await store.set_self_color("group:20001", "10001", "黑桃")
    monkeypatch.setattr(fun, "require_fun", allow_fun)
    monkeypatch.setattr(fun, "get_today", lambda: fixed_day)
    monkeypatch.setattr(fun, "state_store", store)
    fortune = pick_daily_fortune("10001", fixed_day)
    expected = MessageSegment.image(
        await render_fortune_card(
            fortune,
            fixed_day.isoformat(),
            "群名片桃",
            "10001",
            "黑桃",
        )
    )

    async with app.test_matcher(fun.daily_fortune) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("今日桃签", nickname="昵称桃", card="群名片桃")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_lexicon_command_with_term(app: App) -> None:
    entry = BUILTIN_LEXICON.find("黑桃")
    assert entry is not None
    expected = MessageSegment.image(
        await render_lexicon_card(entry, show_sources=True),
    )

    async with app.test_matcher(lexicon_command) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("桃系词典 黑桃")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_lexicon_command_without_term_lists_entries(app: App) -> None:
    body = (
        "已收录桃系词条：\n"
        f"{BUILTIN_LEXICON.list_terms()}\n\n"
        "用法：桃系词典 黑桃"
    )
    expected = MessageSegment.image(
        await render_message_card(
            "桃系词典",
            body,
            chips=("有出处", "可修订"),
            footer="输入“桃系词典 词条名”查看解释、边界和来源。",
        )
    )

    async with app.test_matcher(lexicon_command) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("桃系词典")
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
        event = make_group_event("桃系词典 黑桃")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_user_can_select_color_without_slash(
    app: App,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def allow_fun(*args, **kwargs) -> None:
        return None

    store = TaoziStateStore(tmp_path / "state.json")
    monkeypatch.setattr(fun, "require_fun", allow_fun)
    monkeypatch.setattr(fun, "state_store", store)
    expected = MessageSegment.image(
        await render_message_card(
            "桃色设置成功",
            render_color_selected("黑桃"),
            chips=("黑桃", "自愿选择"),
            footer="这只是插件内的玩笑身份；发送“我的桃色 取消”即可移除。",
        )
    )

    async with app.test_matcher(fun.self_color) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("我的桃色 黑桃")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()

    assert await store.get_self_color("group:20001", "10001") == "黑桃"


@pytest.mark.asyncio
async def test_group_color_chart_only_displays_counts(
    app: App,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def allow_fun(*args, **kwargs) -> None:
        return None

    store = TaoziStateStore(tmp_path / "state.json")
    await store.set_self_color("group:20001", "10001", "黑桃")
    await store.set_self_color("group:20001", "10002", "黑桃")
    await store.set_self_color("group:20001", "10003", "白桃")
    await store.set_self_color("group:99999", "10004", "黄桃")
    monkeypatch.setattr(fun, "require_fun", allow_fun)
    monkeypatch.setattr(fun, "state_store", store)
    body, total = render_color_distribution({"黑桃": 2, "白桃": 1})
    expected = MessageSegment.image(
        await render_message_card(
            "群桃图鉴",
            body,
            chips=(f"已选择 {total} 人", "仅统计人数"),
            footer="桃色均由群友本人主动选择；插件不会自动判断或公开名单。",
        )
    )

    async with app.test_matcher(fun.color_chart) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("群桃图鉴")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_color_chart_rejects_private_message(app: App) -> None:
    expected = MessageSegment.image(
        await render_message_card(
            "仅限群聊",
            "群桃图鉴只统计当前群聊，私聊中无法查看。",
            chips=("不公开名单",),
        )
    )

    async with app.test_matcher(fun.color_chart) as ctx:
        bot = create_onebot(ctx)
        event = make_private_event("群桃图鉴")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_random_term_has_persistent_hourly_cooldown(
    app: App,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def allow_fun(*args, **kwargs) -> None:
        return None

    store = TaoziStateStore(tmp_path / "state.json")
    await store.acquire_random_term("group:20001", "10001", 3600, now=time())
    monkeypatch.setattr(fun, "require_fun", allow_fun)
    monkeypatch.setattr(fun, "state_store", store)
    monkeypatch.setattr(fun, "random_term_notice_cooldown", Cooldown(60))
    expected = MessageSegment.image(
        await render_message_card(
            "随机桃词冷却中",
            "每位群友每小时可抽取一次，还需等待约 60 分钟。",
            chips=("防刷屏", "每群单独计算"),
        )
    )

    async with app.test_matcher(fun.random_term) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("随机桃词")
        ctx.receive_event(bot, event)
        ctx.should_call_send(event, expected, result=None, bot=bot)
        ctx.should_finished()

    async with app.test_matcher(fun.random_term) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("随机桃词")
        ctx.receive_event(bot, event)
        ctx.should_finished()


@pytest.mark.asyncio
async def test_fun_settings_rejects_group_member(app: App) -> None:
    async with app.test_matcher(settings.fun_settings) as ctx:
        bot = create_onebot(ctx)
        event = make_group_event("桃趣 关闭", role="member")
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
        event = make_group_event("桃趣 关闭", role="admin")
        ctx.receive_event(bot, event)
        ctx.should_call_send(
            event,
            expected,
            result=None,
            bot=bot,
        )
        ctx.should_finished()

    assert not await store.is_group_enabled("20001", default=True)
