from __future__ import annotations

from collections.abc import Awaitable, Callable

from nonebot import logger
from nonebot.adapters.onebot.v11 import MessageSegment
from nonebot.matcher import Matcher

from .config import plugin_config
from .fortune import Fortune
from .models import LexiconEntry
from .render import render_fortune_card, render_lexicon_card, render_message_card

ImageFactory = Callable[[], Awaitable[bytes]]


async def _finish_image_or_text(
    matcher: type[Matcher],
    image_factory: ImageFactory,
    fallback_text: str,
) -> None:
    if plugin_config.taozi_image_enabled:
        try:
            image = await image_factory()
        except Exception:
            logger.exception("[taozi] 图片生成失败，准备降级为纯文本")
        else:
            if image:
                await matcher.finish(MessageSegment.image(image))

    if plugin_config.taozi_image_fallback_text or not plugin_config.taozi_image_enabled:
        await matcher.finish(fallback_text)
    await matcher.finish("图片生成失败，请检查 TAOZI_FONT 与 Skia 运行环境。")


async def finish_lexicon_card(
    matcher: type[Matcher],
    entry: LexiconEntry,
    fallback_text: str,
    *,
    compact: bool = False,
) -> None:
    await _finish_image_or_text(
        matcher,
        lambda: render_lexicon_card(
            entry,
            show_sources=plugin_config.taozi_lexicon_show_sources,
            compact=compact,
        ),
        fallback_text,
    )


async def finish_fortune_card(
    matcher: type[Matcher],
    fortune: Fortune,
    day: str,
    owner_name: str,
    owner_id: str,
    selected_color: str | None,
    fallback_text: str,
) -> None:
    await _finish_image_or_text(
        matcher,
        lambda: render_fortune_card(
            fortune,
            day,
            owner_name,
            owner_id,
            selected_color,
        ),
        fallback_text,
    )


async def finish_message_card(
    matcher: type[Matcher],
    title: str,
    body: str,
    *,
    fallback_text: str | None = None,
    chips: tuple[str, ...] = (),
    footer: str = "图片生成失败时会自动回退为纯文本。",
) -> None:
    await _finish_image_or_text(
        matcher,
        lambda: render_message_card(title, body, chips=chips, footer=footer),
        fallback_text if fallback_text is not None else body,
    )
