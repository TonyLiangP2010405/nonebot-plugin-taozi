"""Skia PNG card rendering without Chromium.

The deployment approach follows the user-provided MIT-licensed
nonebot-plugin-daily-attendance project: native Skia drawing, system CJK font
discovery, and PNG bytes sent directly through OneBot. This module keeps all
CPU-bound drawing behind asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import io
import os
import re
from dataclasses import dataclass
from pathlib import Path

import qrcode
import skia
from nonebot import logger

from .fortune import Fortune
from .interactions import get_color_fortune_note
from .models import LexiconEntry

WIDTH = 760
OUTER_PADDING = 24
CONTENT_X = 64
CONTENT_WIDTH = WIDTH - CONTENT_X * 2
MIN_HEIGHT = 430

COLOR_BG_START = "#FFF1F4"
COLOR_BG_END = "#FFE9DD"
COLOR_CARD = "#FFFFFF"
COLOR_SECTION = "#FFF8FA"
COLOR_PRIMARY = "#D84F6A"
COLOR_ACCENT = "#FF8298"
COLOR_TEXT = "#292536"
COLOR_MUTED = "#7B7484"
COLOR_RULE = "#F0DDE2"
COLOR_GREEN = "#DFF4E7"
COLOR_GREEN_TEXT = "#377754"
COLOR_GOLD = "#FFF0CD"
COLOR_GOLD_TEXT = "#8B6820"
COLOR_GRAY = "#ECEAF0"
COLOR_GRAY_TEXT = "#625D69"
COLOR_EYE_BLUE = "#234E7C"

_FONT_CONFIG = ""
_TYPEFACE_CACHE: dict[str, skia.Typeface] = {}
_CHARACTER_IMAGE: skia.Image | None = None
_CHARACTER_IMAGE_LOADED = False
_BV_RE = re.compile(r"\b(BV[0-9A-Za-z]+)\b")
_CHARACTER_PATH = Path(__file__).parent / "resources" / "taozi_character.png"


@dataclass(frozen=True, slots=True)
class CardSection:
    label: str
    body: str


@dataclass(frozen=True, slots=True)
class CardTheme:
    bg_start: str
    bg_end: str
    primary: str
    accent: str
    section: str
    chip_fill: str
    chip_text: str


DEFAULT_CARD_THEME = CardTheme(
    bg_start=COLOR_BG_START,
    bg_end=COLOR_BG_END,
    primary=COLOR_PRIMARY,
    accent=COLOR_ACCENT,
    section=COLOR_SECTION,
    chip_fill="#FFE7EC",
    chip_text=COLOR_PRIMARY,
)

FORTUNE_COLOR_THEMES = {
    "白桃": CardTheme("#FFF8F4", "#FDE9EB", "#A95068", "#F3A8B8", "#FFF8F8", "#FCE8ED", "#91465A"),
    "黑桃": CardTheme("#EFEDF5", "#DDD9E9", "#514966", "#716687", "#F5F3F8", "#E6E1EE", "#514966"),
    "红桃": CardTheme("#FFF0F1", "#FFE0DA", "#C74656", "#EA6672", "#FFF6F6", "#FFE2E5", "#A93848"),
    "黄桃": CardTheme("#FFF8E7", "#FFE9B7", "#9A6A18", "#E8B64D", "#FFFAEE", "#FFF0C8", "#7E5716"),
}


@dataclass(frozen=True, slots=True)
class CardSpec:
    title: str
    subtitle: str
    chips: tuple[str, ...]
    sections: tuple[CardSection, ...]
    footer: str
    qr_url: str | None = None
    qr_label: str | None = None
    theme: CardTheme = DEFAULT_CARD_THEME


@dataclass(frozen=True, slots=True)
class PreparedSection:
    label: str
    body_lines: tuple[str, ...]
    height: float


def init_font_config(font_config: str) -> None:
    global _FONT_CONFIG
    _FONT_CONFIG = font_config.strip()
    _TYPEFACE_CACHE.clear()


def _color(value: str) -> int:
    value = value.lstrip("#")
    return skia.ColorSetARGB(
        255,
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
    )


def _font_candidates() -> list[str]:
    configured = [item.strip() for item in _FONT_CONFIG.split(";") if item.strip()]
    return [
        *configured,
        # Linux
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKsc-Regular.otf",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/arphic/ukai.ttc",
        # Windows
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        # macOS
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]


def _find_typeface() -> skia.Typeface:
    cache_key = _FONT_CONFIG or "__auto__"
    if cache_key in _TYPEFACE_CACHE:
        return _TYPEFACE_CACHE[cache_key]

    for path in _font_candidates():
        try:
            if os.path.isfile(path):
                typeface = skia.Typeface.MakeFromFile(path, 0)
                if typeface is not None:
                    _TYPEFACE_CACHE[cache_key] = typeface
                    logger.info(f"[taozi] 图片字体：{os.path.basename(path)}")
                    return typeface
        except Exception:
            continue

    font_manager = skia.FontMgr()
    for family in (
        "Noto Sans CJK SC",
        "Noto Sans SC",
        "Microsoft YaHei",
        "PingFang SC",
        "WenQuanYi Micro Hei",
        "SimHei",
        "sans-serif",
    ):
        typeface = font_manager.matchFamilyStyle(family, skia.FontStyle.Normal())
        if typeface is not None:
            _TYPEFACE_CACHE[cache_key] = typeface
            return typeface

    logger.warning("[taozi] 未找到中文字体，图片可能出现缺字；请配置 TAOZI_FONT")
    typeface = skia.Typeface(None)
    _TYPEFACE_CACHE[cache_key] = typeface
    return typeface


def _font(size: float, *, bold: bool = False) -> skia.Font:
    font = skia.Font(_find_typeface(), size)
    if bold:
        font.setEmbolden(True)
    return font


def _measure(text: str, font: skia.Font) -> float:
    return font.measureText(text, skia.TextEncoding.kUTF8)


def _wrap_text(text: str, font: skia.Font, max_width: float) -> tuple[str, ...]:
    lines: list[str] = []
    for paragraph in str(text).splitlines() or [""]:
        if not paragraph:
            lines.append("")
            continue

        current = ""
        for character in paragraph:
            candidate = current + character
            if not current or _measure(candidate, font) <= max_width:
                current = candidate
                continue
            lines.append(current.rstrip())
            current = character.lstrip()
        lines.append(current.rstrip())
    return tuple(lines)


def _draw_line(
    canvas: skia.Canvas,
    text: str,
    x: float,
    top: float,
    font: skia.Font,
    color: int,
) -> None:
    metrics = font.getMetrics()
    baseline = top - metrics.fAscent
    canvas.drawString(text, x, baseline, font, skia.Paint(AntiAlias=True, Color=color))


def _prepare_sections(sections: tuple[CardSection, ...]) -> tuple[PreparedSection, ...]:
    body_font = _font(24)
    prepared: list[PreparedSection] = []
    for section in sections:
        body_lines = _wrap_text(section.body, body_font, CONTENT_WIDTH - 48)
        label_height = 30 if section.label else 0
        height = 24 + label_height + len(body_lines) * 36 + 18
        prepared.append(PreparedSection(section.label, body_lines, height))
    return tuple(prepared)


def _chip_colors(text: str, theme: CardTheme) -> tuple[int, int]:
    if "高" in text:
        return _color(COLOR_GREEN), _color(COLOR_GREEN_TEXT)
    if "中" in text:
        return _color(COLOR_GOLD), _color(COLOR_GOLD_TEXT)
    if "低" in text:
        return _color(COLOR_GRAY), _color(COLOR_GRAY_TEXT)
    return _color(theme.chip_fill), _color(theme.chip_text)


def _chip_width(text: str) -> float:
    return _measure(text, _font(18, bold=True)) + 30


def _chip_rows(chips: tuple[str, ...]) -> tuple[tuple[str, ...], ...]:
    rows: list[list[str]] = [[]]
    used = 0.0
    for chip in chips:
        width = _chip_width(chip)
        gap = 10 if rows[-1] else 0
        if rows[-1] and used + gap + width > CONTENT_WIDTH:
            rows.append([])
            used = 0.0
            gap = 0
        rows[-1].append(chip)
        used += gap + width
    return tuple(tuple(row) for row in rows if row)


def _qr_image(url: str) -> skia.Image | None:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=5,
        border=2,
    )
    qr.add_data(url)
    qr.make(fit=True)
    pil_image = qr.make_image(fill_color=COLOR_TEXT, back_color="white").convert("RGB")
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    return skia.Image.MakeFromEncoded(buffer.getvalue())


def _load_character_image() -> skia.Image | None:
    global _CHARACTER_IMAGE, _CHARACTER_IMAGE_LOADED
    if _CHARACTER_IMAGE_LOADED:
        return _CHARACTER_IMAGE

    _CHARACTER_IMAGE_LOADED = True
    try:
        _CHARACTER_IMAGE = skia.Image.MakeFromEncoded(_CHARACTER_PATH.read_bytes())
    except Exception:
        logger.exception("[taozi] 角色背景素材加载失败")
    return _CHARACTER_IMAGE


def _draw_character_background(canvas: skia.Canvas) -> None:
    image = _load_character_image()
    if image is None:
        return

    target_height = 228.0
    target_width = target_height * image.width() / image.height()
    x = CONTENT_X + CONTENT_WIDTH - target_width
    y = OUTER_PADDING + 16

    halo_paint = skia.Paint(AntiAlias=True, Color=_color(COLOR_EYE_BLUE))
    halo_paint.setAlphaf(0.055)
    canvas.drawCircle(x + target_width * 0.58, y + 94, 112, halo_paint)

    character_paint = skia.Paint(AntiAlias=True)
    character_paint.setAlphaf(0.68)
    canvas.drawImageRect(
        image,
        skia.Rect.MakeXYWH(x, y, target_width, target_height),
        skia.SamplingOptions(skia.CubicResampler.Mitchell()),
        character_paint,
    )


def _render_card_sync(spec: CardSpec) -> bytes:
    title_font = _font(44, bold=True)
    title_lines = _wrap_text(spec.title, title_font, CONTENT_WIDTH - 210)
    chip_rows = _chip_rows(spec.chips)
    prepared_sections = _prepare_sections(spec.sections)
    footer_lines = _wrap_text(spec.footer, _font(17), CONTENT_WIDTH)

    header_height = 52 + 28 + len(title_lines) * 56
    chip_height = len(chip_rows) * 44 + (12 if chip_rows else 0)
    sections_height = sum(section.height + 16 for section in prepared_sections)
    qr_height = 154 if spec.qr_url else 0
    footer_height = len(footer_lines) * 24 + 42
    height = int(
        max(
            MIN_HEIGHT,
            OUTER_PADDING * 2
            + 40
            + header_height
            + chip_height
            + sections_height
            + qr_height
            + footer_height,
        )
    )

    surface = skia.Surface(WIDTH, height)
    canvas = surface.getCanvas()

    gradient = skia.GradientShader.MakeLinear(
        [(0, 0), (WIDTH, height)],
        [_color(spec.theme.bg_start), _color(spec.theme.bg_end)],
        None,
        skia.TileMode.kClamp,
    )
    background = skia.Paint(AntiAlias=True)
    background.setShader(gradient)
    canvas.drawRect(skia.Rect.MakeWH(WIDTH, height), background)

    outer = skia.RRect.MakeRectXY(
        skia.Rect.MakeXYWH(
            OUTER_PADDING,
            OUTER_PADDING,
            WIDTH - OUTER_PADDING * 2,
            height - OUTER_PADDING * 2,
        ),
        28,
        28,
    )
    canvas.drawRRect(outer, skia.Paint(AntiAlias=True, Color=_color(COLOR_CARD)))
    canvas.drawRoundRect(
        skia.Rect.MakeXYWH(OUTER_PADDING, OUTER_PADDING, 12, height - OUTER_PADDING * 2),
        6,
        6,
        skia.Paint(AntiAlias=True, Color=_color(spec.theme.accent)),
    )
    _draw_character_background(canvas)

    y = 58.0
    subtitle_font = _font(18, bold=True)
    _draw_line(
        canvas,
        spec.subtitle.upper(),
        CONTENT_X,
        y,
        subtitle_font,
        _color(spec.theme.primary),
    )
    y += 34
    for line in title_lines:
        _draw_line(canvas, line, CONTENT_X, y, title_font, _color(COLOR_TEXT))
        y += 56

    for row in chip_rows:
        x = float(CONTENT_X)
        for chip in row:
            width = _chip_width(chip)
            fill, text_color = _chip_colors(chip, spec.theme)
            pill = skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, width, 32), 16, 16)
            canvas.drawRRect(pill, skia.Paint(AntiAlias=True, Color=fill))
            _draw_line(canvas, chip, x + 15, y + 5, _font(18, bold=True), text_color)
            x += width + 10
        y += 44
    if chip_rows:
        y += 8

    for section in prepared_sections:
        section_rect = skia.RRect.MakeRectXY(
            skia.Rect.MakeXYWH(CONTENT_X, y, CONTENT_WIDTH, section.height),
            18,
            18,
        )
        canvas.drawRRect(
            section_rect,
            skia.Paint(AntiAlias=True, Color=_color(spec.theme.section)),
        )
        text_y = y + 20
        if section.label:
            _draw_line(
                canvas,
                section.label,
                CONTENT_X + 24,
                text_y,
                _font(18, bold=True),
                _color(spec.theme.primary),
            )
            text_y += 30
        for line in section.body_lines:
            _draw_line(
                canvas,
                line,
                CONTENT_X + 24,
                text_y,
                _font(24),
                _color(COLOR_TEXT),
            )
            text_y += 36
        y += section.height + 16

    if spec.qr_url:
        canvas.drawLine(
            CONTENT_X,
            y + 4,
            CONTENT_X + CONTENT_WIDTH,
            y + 4,
            skia.Paint(AntiAlias=True, Color=_color(COLOR_RULE), StrokeWidth=2),
        )
        qr_label = spec.qr_label or "扫码打开代表出处"
        _draw_line(
            canvas,
            qr_label,
            CONTENT_X,
            y + 34,
            _font(20, bold=True),
            _color(COLOR_TEXT),
        )
        url_lines = _wrap_text(spec.qr_url, _font(16), CONTENT_WIDTH - 150)
        url_y = y + 68
        for line in url_lines[:3]:
            _draw_line(canvas, line, CONTENT_X, url_y, _font(16), _color(COLOR_MUTED))
            url_y += 23

        qr_image = _qr_image(spec.qr_url)
        if qr_image is not None:
            canvas.drawImageRect(
                qr_image,
                skia.Rect.MakeXYWH(CONTENT_X + CONTENT_WIDTH - 120, y + 18, 112, 112),
                skia.SamplingOptions(),
                skia.Paint(AntiAlias=True),
            )
        y += 154

    canvas.drawLine(
        CONTENT_X,
        y,
        CONTENT_X + CONTENT_WIDTH,
        y,
        skia.Paint(AntiAlias=True, Color=_color(COLOR_RULE), StrokeWidth=2),
    )
    y += 18
    for line in footer_lines:
        _draw_line(canvas, line, CONTENT_X, y, _font(17), _color(COLOR_MUTED))
        y += 24

    image = surface.makeImageSnapshot()
    encoded = image.encodeToData(skia.EncodedImageFormat.kPNG, 100) or image.encodeToData()
    if encoded is None:
        raise RuntimeError("Skia PNG 编码失败")
    return bytes(encoded)


def _source_text(entry: LexiconEntry, *, compact: bool) -> str:
    sources = entry.sources[:1] if compact else entry.sources
    lines: list[str] = []
    for index, source in enumerate(sources, start=1):
        bv_match = _BV_RE.search(source.url)
        identifier = bv_match.group(1) if bv_match else source.url
        lines.append(f"{index}. {source.title}")
        lines.append(identifier)
    return "\n".join(lines)


async def render_lexicon_card(
    entry: LexiconEntry,
    *,
    show_sources: bool,
    compact: bool = False,
) -> bytes:
    sections = []
    if entry.aliases and not compact:
        sections.append(CardSection("别名", "、".join(entry.aliases)))
    sections.extend(
        [
            CardSection("解释", entry.meaning),
            CardSection("语境边界", entry.boundary),
        ]
    )
    if show_sources:
        sections.append(CardSection("代表出处", _source_text(entry, compact=compact)))

    first_source = entry.sources[0] if show_sources else None
    spec = CardSpec(
        title=entry.term,
        subtitle="桃系词典 · 非官方粉丝整理",
        chips=(
            entry.subject,
            f"可信度 {entry.confidence}",
            f"核验 {entry.verified_at}",
        ),
        sections=tuple(sections),
        footer="词义会随直播与二创语境变化，请结合原始出处理解。",
        qr_url=first_source.url if first_source else None,
        qr_label="扫码打开第一条代表出处",
    )
    return await asyncio.to_thread(_render_card_sync, spec)


async def render_fortune_card(
    fortune: Fortune,
    day: str,
    owner_name: str,
    owner_id: str,
    selected_color: str | None = None,
) -> bytes:
    chips = [f"关键词 {fortune.keyword}", "仅供娱乐"]
    sections = [
        CardSection("桃签主人", f"{owner_name}（账号 {owner_id}）"),
        CardSection("今日提示", fortune.message),
    ]
    color_note = get_color_fortune_note(selected_color)
    if selected_color and color_note:
        chips.insert(0, f"自选 {selected_color}")
        sections.append(CardSection(f"{selected_color}附言", color_note))

    spec = CardSpec(
        title=fortune.name,
        subtitle=f"今日桃签 · {day}",
        chips=tuple(chips),
        sections=tuple(sections),
        footer="互动文案不是主播原话；同一账号当天固定，次日重新抽取。",
        theme=FORTUNE_COLOR_THEMES.get(selected_color or "", DEFAULT_CARD_THEME),
    )
    return await asyncio.to_thread(_render_card_sync, spec)


async def render_message_card(
    title: str,
    body: str,
    *,
    subtitle: str = "桃纸助手 · 非官方粉丝插件",
    chips: tuple[str, ...] = (),
    footer: str = "图片生成失败时会自动回退为纯文本。",
) -> bytes:
    spec = CardSpec(
        title=title,
        subtitle=subtitle,
        chips=chips,
        sections=(CardSection("", body),),
        footer=footer,
    )
    return await asyncio.to_thread(_render_card_sync, spec)
