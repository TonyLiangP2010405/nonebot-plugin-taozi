from io import BytesIO

import pytest
from PIL import Image

from nonebot_plugin_taozi.fortune import FORTUNES
from nonebot_plugin_taozi.lexicon import BUILTIN_LEXICON
from nonebot_plugin_taozi.render import (
    _CHARACTER_PATH,
    WIDTH,
    render_fortune_card,
    render_lexicon_card,
    render_message_card,
)


def assert_valid_png(data: bytes, *, minimum_height: int = 430) -> None:
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(data) > 10_000
    with Image.open(BytesIO(data)) as image:
        assert image.format == "PNG"
        assert image.width == WIDTH
        assert image.height >= minimum_height


def test_character_background_asset_is_transparent_png() -> None:
    with Image.open(_CHARACTER_PATH) as image:
        assert image.format == "PNG"
        assert image.mode == "RGBA"
        alpha = image.getchannel("A")
        assert alpha.getextrema() == (0, 255)
        assert alpha.getbbox() is not None


@pytest.mark.asyncio
async def test_lexicon_card_is_png_with_dynamic_height() -> None:
    entry = BUILTIN_LEXICON.find("黑桃")
    assert entry is not None
    data = await render_lexicon_card(entry, show_sources=True)
    assert_valid_png(data, minimum_height=900)


@pytest.mark.asyncio
async def test_fortune_card_is_png() -> None:
    data = await render_fortune_card(FORTUNES[0], "2026-07-30")
    assert_valid_png(data)


@pytest.mark.asyncio
async def test_message_card_grows_for_long_content() -> None:
    data = await render_message_card(
        "桃纸助手",
        "\n".join(f"第 {index} 行：这是一段用于验证动态高度的中文内容。" for index in range(20)),
        chips=("非官方", "图片模式"),
    )
    assert_valid_png(data, minimum_height=1100)
