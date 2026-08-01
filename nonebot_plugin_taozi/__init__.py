from nonebot import require
from nonebot.plugin import PluginMetadata

from .config import Config, plugin_config
from .render import init_font_config

require("nonebot_plugin_localstore")
init_font_config(plugin_config.taozi_font)

__plugin_meta__ = PluginMetadata(
    name="桃纸助手",
    description="图片化的有出处桃系词典与可选轻互动",
    usage=(
        "桃系词典 [词条]｜随机桃词｜今日桃签｜我的桃色 [桃色/取消]｜"
        "群桃图鉴｜桃趣状态｜桃趣 开启/关闭"
    ),
    type="application",
    homepage="https://github.com/TonyLiangP2010405/nonebot-plugin-taozi",
    config=Config,
    supported_adapters={"~onebot.v11"},
    extra={
        "authoritative": False,
        "disclaimer": "非官方粉丝插件；词条含义以公开来源和具体语境为准。",
    },
)

from .commands import fun as fun
from .commands import help as help
from .commands import lexicon as lexicon
from .commands import settings as settings
