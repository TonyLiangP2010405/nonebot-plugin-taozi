from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.params import CommandArg

from ..config import plugin_config
from ..lexicon import BUILTIN_LEXICON, render_entry
from ..output import finish_lexicon_card, finish_message_card

lexicon_command = on_command(
    "桃系词典",
    aliases={"桃词典"},
    priority=10,
    block=True,
)


@lexicon_command.handle()
async def handle_lexicon(args: Message = CommandArg()) -> None:
    query = args.extract_plain_text().strip()
    if not query:
        body = (
            "已收录桃系词条：\n"
            f"{BUILTIN_LEXICON.list_terms()}\n\n"
            "用法：/桃系词典 黑桃"
        )
        await finish_message_card(
            lexicon_command,
            "桃系词典",
            body,
            chips=("有出处", "可修订"),
            footer="输入“/桃系词典 词条名”查看解释、边界和来源。",
        )

    entry = BUILTIN_LEXICON.find(query)
    if entry is None:
        suggestions = BUILTIN_LEXICON.suggest(query)
        suffix = f"\n你可能想查：{'、'.join(suggestions)}" if suggestions else ""
        body = (
            f"暂未收录“{query}”。{suffix}\n"
            "词典只收录有公开出处、能说明边界的用法。"
        )
        await finish_message_card(
            lexicon_command,
            "暂未收录",
            body,
            chips=("等待考证",),
            footer="有可靠公开来源后，可以通过更新词典数据补充。",
        )

    await finish_lexicon_card(
        lexicon_command,
        entry,
        render_entry(entry, show_sources=plugin_config.taozi_lexicon_show_sources),
    )
