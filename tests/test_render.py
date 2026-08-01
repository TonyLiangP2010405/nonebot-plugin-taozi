from io import BytesIO

import pytest
from PIL import Image

from nonebot_plugin_taozi import render
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
@pytest.mark.parametrize("selected_color", ("白桃", "黑桃", "红桃", "黄桃"))
async def test_each_color_fortune_card_is_png(selected_color: str) -> None:
    data = await render_fortune_card(
        FORTUNES[0],
        "2026-07-30",
        "测试桃",
        "10001",
        selected_color,
    )
    assert_valid_png(data)


@pytest.mark.asyncio
async def test_fortune_card_has_explicit_owner_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[render.CardSpec] = []

    def capture_spec(spec: render.CardSpec) -> bytes:
        captured.append(spec)
        return b"rendered"

    monkeypatch.setattr(render, "_render_card_sync", capture_spec)
    data = await render.render_fortune_card(
        FORTUNES[0],
        "2026-07-31",
        "群名片桃",
        "10001",
        "黑桃",
    )

    assert data == b"rendered"
    assert captured[0].subtitle == "今日桃签 · 2026-07-31"
    assert captured[0].sections[0].label == "桃签主人"
    assert captured[0].sections[0].body == "群名片桃（账号 10001）"
    assert captured[0].chips[0] == "自选 黑桃"
    assert captured[0].sections[-1].label == "黑桃附言"
    assert "玩笑" in captured[0].sections[-1].body
    assert captured[0].theme == render.FORTUNE_COLOR_THEMES["黑桃"]


@pytest.mark.asyncio
async def test_message_card_grows_for_long_content() -> None:
    data = await render_message_card(
        "桃纸助手",
        "\n".join(f"第 {index} 行：这是一段用于验证动态高度的中文内容。" for index in range(20)),
        chips=("非官方", "图片模式"),
    )
    assert_valid_png(data, minimum_height=1100)
