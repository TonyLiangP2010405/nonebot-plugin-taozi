from nonebot import on_command

from ..output import finish_message_card

help_command = on_command(
    "桃纸帮助",
    aliases={"桃纸助手"},
    priority=10,
    block=True,
)


@help_command.handle()
async def handle_help() -> None:
    body = (
        "词典：/桃系词典 [词条]\n"
        "随机词条：/随机桃词\n"
        "每日互动：今日桃签（无需斜杠；同账号当天固定）\n"
        "自选身份：/我的桃色 [白桃/黑桃/红桃/黄桃/取消]\n"
        "互动状态：/桃趣状态\n"
        "群管理：/桃趣 开启｜关闭｜状态\n\n"
        "词典保留出处、可信度和语境边界；互动文案不是主播原话。"
    )
    await finish_message_card(
        help_command,
        "桃纸助手",
        body,
        chips=("非官方", "图片模式"),
        footer="有出处的桃系词典 · 可选的轻互动",
    )
