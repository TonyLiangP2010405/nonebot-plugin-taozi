from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    """桃纸助手配置。所有配置均有默认值，插件可零配置加载。"""

    taozi_fun_enabled: bool = True
    taozi_fun_cooldown_seconds: int = Field(default=8, ge=0, le=300)
    taozi_random_term_cooldown_seconds: int = Field(default=3600, ge=0, le=86400)
    taozi_lexicon_show_sources: bool = True
    taozi_timezone: str = "Asia/Shanghai"
    taozi_image_enabled: bool = True
    taozi_image_fallback_text: bool = True
    taozi_font: str = ""


plugin_config = get_plugin_config(Config)
