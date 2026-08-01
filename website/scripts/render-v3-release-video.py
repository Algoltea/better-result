#!/usr/bin/env python3
# Requires Python 3.11+, Pillow 11+, and ffmpeg.
"""Render the better-result 3.0 release announcement video.

The animation mirrors the dark Blume documentation theme: monochrome surfaces,
a restrained grid, compact borders, and the site's #1687d9 sky-blue accent.
Frames stream directly to ffmpeg so rendering does not create a large image sequence.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 1920
HEIGHT = 1080
RENDER_SCALE = 2
OUTPUT_WIDTH = WIDTH * RENDER_SCALE
OUTPUT_HEIGHT = HEIGHT * RENDER_SCALE
FPS = 30
DURATION_SECONDS = 38

BACKGROUND = "#1b1b1b"
SURFACE = "#202020"
SURFACE_RAISED = "#272727"
FOREGROUND = "#fafafa"
MUTED = "#b7b7b7"
MUTED_DARK = "#777777"
BORDER = "#454545"
GRID = "#252525"
ACCENT = "#1687d9"
ACCENT_LIGHT = "#78c9f4"
ACCENT_DARK = "#0d568e"
SUCCESS = "#78c9f4"
WHITE = "#ffffff"

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "media" / "better-result-v3-release.mp4"

FONT_REGULAR = "/System/Library/Fonts/SFNS.ttf"
FONT_BOLD = "/System/Library/Fonts/SFNS.ttf"
FONT_MONO = "/System/Library/Fonts/SFNSMono.ttf"


class ScaledDraw:
    """Draw logical 1920×1080 coordinates onto the native-resolution render canvas."""

    def __init__(self, image: Image.Image) -> None:
        self._draw = ImageDraw.Draw(image)

    @staticmethod
    def _point(point: tuple[float, float]) -> tuple[float, float]:
        return (point[0] * RENDER_SCALE, point[1] * RENDER_SCALE)

    @staticmethod
    def _box(box: tuple[float, float, float, float]) -> tuple[float, float, float, float]:
        return tuple(value * RENDER_SCALE for value in box)

    def line(self, coordinates, *, fill, width=1) -> None:
        self._draw.line(
            tuple(value * RENDER_SCALE for value in coordinates),
            fill=fill,
            width=max(1, round(width * RENDER_SCALE)),
        )

    def ellipse(self, box, *, fill=None, outline=None, width=1) -> None:
        self._draw.ellipse(
            self._box(box),
            fill=fill,
            outline=outline,
            width=max(1, round(width * RENDER_SCALE)),
        )

    def polygon(self, points, *, fill) -> None:
        self._draw.polygon(tuple(self._point(point) for point in points), fill=fill)

    def rounded_rectangle(self, box, *, radius, fill, outline=None, width=1) -> None:
        self._draw.rounded_rectangle(
            self._box(box),
            radius=round(radius * RENDER_SCALE),
            fill=fill,
            outline=outline,
            width=max(1, round(width * RENDER_SCALE)),
        )

    def text(self, position, value, *, font, fill, anchor=None) -> None:
        self._draw.text(self._point(position), value, font=font, fill=fill, anchor=anchor)

    def multiline_text(self, position, value, *, font, fill, anchor, spacing) -> None:
        self._draw.multiline_text(
            self._point(position),
            value,
            font=font,
            fill=fill,
            anchor=anchor,
            spacing=round(spacing * RENDER_SCALE),
        )

    def textbbox(self, position, value, *, font) -> tuple[float, float, float, float]:
        box = self._draw.textbbox(self._point(position), value, font=font)
        return tuple(value / RENDER_SCALE for value in box)


def font(size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_MONO if mono else FONT_REGULAR
    return ImageFont.truetype(path, size=round(size * RENDER_SCALE))


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def ease(value: float) -> float:
    value = clamp(value)
    return 1 - (1 - value) ** 3


def smoothstep(value: float) -> float:
    value = clamp(value)
    return value * value * (3 - 2 * value)


def scene_visibility(local_time: float, duration: float) -> float:
    enter = smoothstep(local_time / 0.65)
    leave = smoothstep((duration - local_time) / 0.5)
    return min(enter, leave)


def rgba(hex_color: str, alpha: float = 1.0) -> tuple[int, int, int, int]:
    value = hex_color.removeprefix("#")
    return (
        int(value[0:2], 16),
        int(value[2:4], 16),
        int(value[4:6], 16),
        round(255 * clamp(alpha)),
    )


def draw_grid(image: Image.Image, time: float) -> None:
    draw = ScaledDraw(image)
    spacing = 48
    offset = round((time * 7) % spacing)
    for x in range(-spacing + offset, WIDTH, spacing):
        draw.line((x, 0, x, HEIGHT), fill=GRID, width=1)
    for y in range(-spacing + offset, HEIGHT, spacing):
        draw.line((0, y, WIDTH, y), fill=GRID, width=1)

    glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
    glow_draw = ScaledDraw(glow)
    pulse = 0.55 + math.sin(time * 1.4) * 0.08
    glow_draw.ellipse(
        (WIDTH - 610, -270, WIDTH + 250, 590),
        fill=rgba(ACCENT, 0.11 * pulse),
    )
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90 * RENDER_SCALE)))


def rounded_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[float, float, float, float],
    *,
    fill: str,
    outline: str | None = None,
    width: int = 1,
    radius: int = 18,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text(
    draw: ImageDraw.ImageDraw,
    position: tuple[float, float],
    value: str,
    size: int,
    *,
    fill: str = FOREGROUND,
    mono: bool = False,
    anchor: str = "la",
    spacing: int = 8,
) -> None:
    draw.multiline_text(
        position,
        value,
        font=font(size, mono=mono),
        fill=fill,
        anchor=anchor,
        spacing=spacing,
    )


def logo(draw: ImageDraw.ImageDraw, x: float, y: float, size: int) -> None:
    rounded_rect(draw, (x, y, x + size, y + size), fill=ACCENT, radius=round(size * 0.22))
    text(draw, (x + size * 0.5, y + size * 0.51), "R", round(size * 0.62), fill=WHITE, anchor="mm")


def badge(draw: ImageDraw.ImageDraw, x: float, y: float, label: str, *, accent: bool = False) -> int:
    label_font = font(26, mono=True)
    box = draw.textbbox((0, 0), label, font=label_font)
    badge_width = box[2] - box[0] + 38
    rounded_rect(
        draw,
        (x, y, x + badge_width, y + 48),
        fill=ACCENT_DARK if accent else SURFACE_RAISED,
        outline=ACCENT if accent else BORDER,
        radius=10,
    )
    draw.text((x + 19, y + 24), label, font=label_font, fill=FOREGROUND, anchor="lm")
    return badge_width


def scene_layer(opacity: float, offset_y: float = 0) -> tuple[Image.Image, ScaledDraw, float]:
    layer = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), (0, 0, 0, 0))
    return layer, ScaledDraw(layer), offset_y


def composite_scene(base: Image.Image, layer: Image.Image, visibility: float) -> None:
    if visibility < 1:
        alpha = layer.getchannel("A").point(lambda value: round(value * visibility))
        layer.putalpha(alpha)
    base.alpha_composite(layer)


def draw_site_header(draw: ImageDraw.ImageDraw) -> None:
    logo(draw, 92, 72, 52)
    text(draw, (164, 98), "better-result", 30, anchor="lm")
    text(draw, (WIDTH - 92, 98), "better-result.dev", 25, fill=MUTED, mono=True, anchor="rm")


def draw_progress(draw: ImageDraw.ImageDraw, time: float) -> None:
    x1, x2, y = 92, WIDTH - 92, HEIGHT - 62
    draw.line((x1, y, x2, y), fill=BORDER, width=2)
    progress = clamp(time / DURATION_SECONDS)
    draw.line((x1, y, x1 + (x2 - x1) * progress, y), fill=ACCENT, width=4)


def draw_code_window(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    lines: list[tuple[str, str]],
    *,
    title: str = "TypeScript",
    reveal: float = 1.0,
) -> None:
    x1, y1, x2, y2 = box
    rounded_rect(draw, box, fill=SURFACE, outline=BORDER, width=2, radius=18)
    draw.line((x1, y1 + 66, x2, y1 + 66), fill=BORDER, width=2)
    for index, color in enumerate(("#5b5b5b", "#4b4b4b", "#3f3f3f")):
        draw.ellipse((x1 + 24 + index * 26, y1 + 25, x1 + 38 + index * 26, y1 + 39), fill=color)
    text(draw, (x2 - 24, y1 + 33), title, 22, fill=MUTED_DARK, mono=True, anchor="rm")

    visible_lines = clamp(reveal) * len(lines)
    for index, (line, color) in enumerate(lines):
        line_visibility = clamp(visible_lines - index)
        if line_visibility <= 0:
            continue
        text(draw, (x1 + 38, y1 + 108 + index * 46), line, 28, fill=color, mono=True, anchor="la")


def intro_scene(base: Image.Image, local_time: float, duration: float) -> None:
    visibility = scene_visibility(local_time, duration)
    rise = (1 - ease(local_time / 1.1)) * 42
    layer, draw, _ = scene_layer(visibility, rise)
    draw_site_header(draw)

    logo_scale = 104 + round(math.sin(local_time * 2) * 2)
    logo(draw, 204, 306 + rise, logo_scale)
    badge(draw, 204, 446 + rise, "v3.0.0", accent=True)
    text(draw, (204, 545 + rise), "A better Result type\nfor TypeScript.", 84, anchor="la", spacing=4)
    text(
        draw,
        (208, 754 + rise),
        "Typed errors · generator composition · zero dependencies",
        30,
        fill=MUTED,
        mono=True,
    )

    track_x = 1230 + ease(local_time / 1.4) * 110
    draw.line((1100, 382, 1694, 382), fill=BORDER, width=4)
    draw.line((1100, 634, 1694, 634), fill=BORDER, width=4)
    for y, label, accent in ((382, "Ok<T>", True), (634, "Err<E>", False)):
        rounded_rect(
            draw,
            (track_x, y - 47, track_x + 210, y + 47),
            fill=ACCENT_DARK if accent else SURFACE_RAISED,
            outline=ACCENT if accent else BORDER,
            width=2,
            radius=14,
        )
        text(draw, (track_x + 105, y), label, 34, mono=True, anchor="mm")
    composite_scene(base, layer, visibility)


def tagged_error_scene(base: Image.Image, local_time: float, duration: float) -> None:
    visibility = scene_visibility(local_time, duration)
    rise = (1 - ease(local_time / 0.8)) * 34
    layer, draw, _ = scene_layer(visibility, rise)
    draw_site_header(draw)
    badge(draw, 122, 206 + rise, "01 / CLEANER ERRORS", accent=True)
    text(draw, (122, 307 + rise), "TaggedError, simplified.", 70)
    text(draw, (122, 397 + rise), "Props now live where they belong: on the subclass.", 31, fill=MUTED)

    old_box = (122, 500 + round(rise), 900, 755 + round(rise))
    new_box = (1020, 500 + round(rise), 1798, 755 + round(rise))
    draw_code_window(
        draw,
        old_box,
        [("class NotFound extends", MUTED), ('  TaggedError("NotFound")<Props>() {}', MUTED)],
        title="2.x",
    )
    draw_code_window(
        draw,
        new_box,
        [("class NotFound extends", FOREGROUND), ('  TaggedError("NotFound")<Props> {}', ACCENT_LIGHT)],
        title="3.0",
    )
    arrow_progress = ease((local_time - 0.7) / 0.7)
    draw.line((930, 626, 970, 626), fill=ACCENT, width=max(1, round(4 * arrow_progress)))
    draw.polygon(((970, 626), (950, 614), (950, 638)), fill=ACCENT)
    rounded_rect(draw, (122, 802, 420, 854), fill=SURFACE_RAISED, outline=BORDER, radius=10)
    text(draw, (271, 828), "remove trailing ()", 22, fill=MUTED, mono=True, anchor="mm")
    text(draw, (1020, 828), "props supplied by the subclass", 22, fill=ACCENT_LIGHT, mono=True)
    composite_scene(base, layer, visibility)


def matching_scene(base: Image.Image, local_time: float, duration: float) -> None:
    visibility = scene_visibility(local_time, duration)
    slide = (1 - ease(local_time / 0.8)) * 42
    layer, draw, _ = scene_layer(visibility, slide)
    draw_site_header(draw)
    badge(draw, 122, 184 + slide, "02 / EXHAUSTIVE MATCHING", accent=True)
    text(draw, (122, 286 + slide), "Handle every error.\nLet TypeScript check the rest.", 68, spacing=3)

    lines = [
        ("error.match({", FOREGROUND),
        ("  NotFound: () => 404,", ACCENT_LIGHT),
        ("  Unauthorized: () => 401,", ACCENT_LIGHT),
        ("  DatabaseDown: () => 503,", ACCENT_LIGHT),
        ("});", FOREGROUND),
    ]
    draw_code_window(draw, (1045, 208, 1798, 590), lines, reveal=ease((local_time - 0.4) / 1.5))

    labels = (("NotFound", "404"), ("Unauthorized", "401"), ("DatabaseDown", "503"))
    for index, (name, status) in enumerate(labels):
        progress = ease((local_time - 1.6 - index * 0.22) / 0.55)
        x = 1045 + (1 - progress) * 70
        y = 652 + index * 76
        rounded_rect(draw, (x, y, x + 550, y + 58), fill=SURFACE_RAISED, outline=BORDER, radius=10)
        text(draw, (x + 20, y + 29), name, 25, mono=True, anchor="lm")
        rounded_rect(draw, (x + 462, y + 10, x + 530, y + 48), fill=ACCENT_DARK, radius=8)
        text(draw, (x + 496, y + 29), status, 23, mono=True, anchor="mm")
    composite_scene(base, layer, visibility)


def codec_scene(base: Image.Image, local_time: float, duration: float) -> None:
    visibility = scene_visibility(local_time, duration)
    rise = (1 - ease(local_time / 0.8)) * 32
    layer, draw, _ = scene_layer(visibility, rise)
    draw_site_header(draw)
    badge(draw, 122, 146 + rise, "03 / RESULT.CODEC", accent=True)
    text(draw, (122, 238 + rise), "Four schemas. One typed boundary.", 64)
    text(
        draw,
        (122, 322 + rise),
        "Transform domain values to wire values—and safely back again.",
        30,
        fill=MUTED,
    )

    text(draw, (122, 394), "INPUT", 20, fill=MUTED_DARK, mono=True)
    text(draw, (760, 394), "STANDARD SCHEMA", 20, fill=MUTED_DARK, mono=True)
    text(draw, (1398, 394), "OUTPUT", 20, fill=MUTED_DARK, mono=True)

    lanes = (
        ("Domain Ok", 'User { name: "Ada" }', "serialize.ok", "Wire Ok", '{ display_name: "Ada" }'),
        ("Domain Err", "UserNotFound { id }", "serialize.err", "Wire Err", '{ code: "NOT_FOUND" }'),
        ("Wire Ok", '{ display_name: "Ada" }', "deserialize.ok", "Domain Ok", 'User { name: "Ada" }'),
        ("Wire Err", '{ code: "NOT_FOUND" }', "deserialize.err", "Domain Err", "UserNotFound { id }"),
    )

    left_box = (122, 0, 570, 0)
    schema_box = (710, 0, 1210, 0)
    right_box = (1398, 0, 1798, 0)
    for index, (input_label, input_value, schema, output_label, output_value) in enumerate(lanes):
        y = 422 + index * 137
        lane_progress = ease((local_time - 0.45 - index * 0.62) / 0.95)
        left = (left_box[0], y, left_box[2], y + 104)
        middle = (schema_box[0], y + 14, schema_box[2], y + 90)
        right = (right_box[0], y, right_box[2], y + 104)

        rounded_rect(draw, left, fill=SURFACE_RAISED, outline=BORDER, width=2, radius=12)
        text(draw, (left[0] + 24, y + 22), input_label, 18, fill=MUTED, mono=True)
        text(draw, (left[0] + 24, y + 62), input_value, 22, mono=True)

        schema_active = 0.32 <= lane_progress <= 0.84
        rounded_rect(
            draw,
            middle,
            fill=ACCENT_DARK if schema_active else SURFACE,
            outline=ACCENT if schema_active else BORDER,
            width=2,
            radius=12,
        )
        text(draw, ((middle[0] + middle[2]) / 2, y + 52), schema, 25, fill=ACCENT_LIGHT, mono=True, anchor="mm")

        rounded_rect(
            draw,
            right,
            fill=SURFACE_RAISED,
            outline=ACCENT if lane_progress >= 0.92 else BORDER,
            width=2,
            radius=12,
        )
        text(draw, (right[0] + 24, y + 22), output_label, 18, fill=MUTED, mono=True)
        text(draw, (right[0] + 24, y + 62), output_value, 21, mono=True)

        center_y = y + 52
        draw.line((left[2] + 16, center_y, middle[0] - 16, center_y), fill=BORDER, width=3)
        draw.line((middle[2] + 16, center_y, right[0] - 16, center_y), fill=BORDER, width=3)
        first_leg = clamp(lane_progress * 2)
        second_leg = clamp(lane_progress * 2 - 1)
        draw.line(
            (left[2] + 16, center_y, left[2] + 16 + (middle[0] - left[2] - 32) * first_leg, center_y),
            fill=ACCENT,
            width=4,
        )
        draw.line(
            (middle[2] + 16, center_y, middle[2] + 16 + (right[0] - middle[2] - 32) * second_leg, center_y),
            fill=ACCENT,
            width=4,
        )
        if lane_progress < 0.5:
            packet_x = left[2] + 16 + (middle[0] - left[2] - 32) * first_leg
        else:
            packet_x = middle[2] + 16 + (right[0] - middle[2] - 32) * second_leg
        draw.ellipse((packet_x - 8, center_y - 8, packet_x + 8, center_y + 8), fill=ACCENT_LIGHT)

    composite_scene(base, layer, visibility)


def collections_scene(base: Image.Image, local_time: float, duration: float) -> None:
    visibility = scene_visibility(local_time, duration)
    layer, draw, _ = scene_layer(visibility)
    draw_site_header(draw)
    badge(draw, 122, 168, "04 / COLLECTIONS", accent=True)
    text(draw, (122, 270), "Compose more.\nPreserve every type.", 68, spacing=4)

    methods = ("Result.all", "Result.allAsync", "Result.partitionAsync")
    for index, method in enumerate(methods):
        progress = ease((local_time - 0.35 - index * 0.2) / 0.7)
        y = 568 + index * 94
        x = 122 - (1 - progress) * 70
        rounded_rect(draw, (x, y, x + 560, y + 70), fill=SURFACE, outline=BORDER, width=2, radius=12)
        text(draw, (x + 28, y + 35), method, 27, mono=True, anchor="lm")
        text(draw, (x + 518, y + 35), "→", 27, fill=ACCENT_LIGHT, mono=True, anchor="mm")

    input_labels = ("Ok<User>", "Ok<Role>", "Ok<Scope>")
    input_y_positions = (394, 524, 654)
    for index, (label, y) in enumerate(zip(input_labels, input_y_positions, strict=True)):
        progress = ease((local_time - 0.55 - index * 0.28) / 0.65)
        x1, x2 = 880, 1130
        rounded_rect(
            draw,
            (x1, y, x2, y + 86),
            fill=ACCENT_DARK if progress >= 0.95 else SURFACE_RAISED,
            outline=ACCENT if progress >= 0.95 else BORDER,
            width=2,
            radius=12,
        )
        text(draw, ((x1 + x2) / 2, y + 43), label, 24, mono=True, anchor="mm")
        center_y = y + 43
        target_x = 1290
        draw.line((x2 + 18, center_y, target_x - 18, 567), fill=BORDER, width=3)
        line_x = x2 + 18 + (target_x - x2 - 36) * progress
        line_y = center_y + (567 - center_y) * progress
        draw.line((x2 + 18, center_y, line_x, line_y), fill=ACCENT, width=4)

    rounded_rect(draw, (1290, 468, 1518, 666), fill=SURFACE, outline=ACCENT, width=3, radius=18)
    logo(draw, 1370, 500, 68)
    text(draw, (1404, 604), "Result.all", 26, mono=True, anchor="mm")

    output_progress = ease((local_time - 1.65) / 0.7)
    draw.line((1536, 567, 1570, 567), fill=BORDER, width=3)
    draw.line((1536, 567, 1536 + 34 * output_progress, 567), fill=ACCENT, width=4)
    rounded_rect(
        draw,
        (1570, 506, 1820, 628),
        fill=SURFACE_RAISED,
        outline=ACCENT if output_progress >= 0.95 else BORDER,
        width=2,
        radius=14,
    )
    text(draw, (1695, 546), "Ok", 21, fill=MUTED, mono=True, anchor="mm")
    text(draw, (1695, 590), "[User, Role, Scope]", 17, fill=ACCENT_LIGHT, mono=True, anchor="mm")
    text(draw, (880, 806), "tuple order preserved  ·  errors stay typed", 23, fill=MUTED, mono=True)
    composite_scene(base, layer, visibility)


def retry_scene(base: Image.Image, local_time: float, duration: float) -> None:
    visibility = scene_visibility(local_time, duration)
    layer, draw, _ = scene_layer(visibility)
    draw_site_header(draw)
    badge(draw, 122, 168, "05 / RETRIES + RECOVERY", accent=True)
    text(draw, (122, 274), "Smarter retries.\nDeterministic failure recovery.", 58, spacing=5)
    text(draw, (122, 480), "AbortSignal · dynamic delays · jitter", 27, fill=MUTED, mono=True)
    text(draw, (122, 540), "tryRecover → Result<A | B, E>", 29, fill=ACCENT_LIGHT, mono=True)

    attempt_boxes = (
        (900, "attempt 1", "Err<Timeout>"),
        (1202, "attempt 2", "Err<Timeout>"),
        (1504, "attempt 3", "Ok<User>"),
    )
    attempt_times = (0.45, 1.9, 3.35)
    for index, ((x, attempt_label, result_label), start_time) in enumerate(zip(attempt_boxes, attempt_times, strict=True)):
        reached = ease((local_time - start_time) / 0.45)
        succeeded = index == 2 and reached >= 0.95
        rounded_rect(
            draw,
            (x, 390, x + 238, 548),
            fill=ACCENT_DARK if succeeded else SURFACE_RAISED,
            outline=ACCENT if reached >= 0.95 else BORDER,
            width=3 if reached >= 0.95 else 2,
            radius=16,
        )
        text(draw, (x + 119, 430), attempt_label, 21, fill=MUTED, mono=True, anchor="mm")
        text(
            draw,
            (x + 119, 493),
            result_label,
            25,
            fill=ACCENT_LIGHT if reached >= 0.95 else MUTED_DARK,
            mono=True,
            anchor="mm",
        )

    delay_specs = ((1138, 1202, 1.05, "delay(error, attempt 1)"), (1440, 1504, 2.5, "delay(error, attempt 2)"))
    for x1, x2, start_time, label in delay_specs:
        delay_progress = ease((local_time - start_time) / 0.72)
        center_y = 469
        draw.line((x1 + 12, center_y, x2 - 12, center_y), fill=BORDER, width=3)
        draw.line((x1 + 12, center_y, x1 + 12 + (x2 - x1 - 24) * delay_progress, center_y), fill=ACCENT, width=4)
        text(draw, ((x1 + x2) / 2, 586), label, 16, fill=MUTED, mono=True, anchor="mm")
        if 0 < delay_progress < 1:
            packet_x = x1 + 12 + (x2 - x1 - 24) * delay_progress
            draw.ellipse((packet_x - 7, center_y - 7, packet_x + 7, center_y + 7), fill=ACCENT_LIGHT)

    signal_progress = ease((local_time - 0.7) / 1.2)
    signal_y = 738
    signal_start_x = 1019
    draw.line((signal_start_x, signal_y, 1810, signal_y), fill=BORDER, width=3)
    draw.line(
        (signal_start_x, signal_y, signal_start_x + 791 * signal_progress, signal_y),
        fill=ACCENT,
        width=4,
    )
    for x, _, _ in attempt_boxes:
        branch_x = x + 119
        draw.line((branch_x, signal_y, branch_x, 570), fill=BORDER, width=2)
        if signal_start_x + 791 * signal_progress >= branch_x:
            draw.line((branch_x, signal_y, branch_x, 570), fill=ACCENT, width=3)
    rounded_rect(draw, (900, 708, 995, 768), fill=SURFACE, outline=BORDER, width=2, radius=10)
    text(draw, (947.5, 738), "signal", 17, fill=ACCENT_LIGHT, mono=True, anchor="mm")

    rounded_rect(draw, (900, 814, 1324, 890), fill=SURFACE, outline=BORDER, width=2, radius=12)
    text(
        draw,
        (1112, 852),
        "context.attempt: 1 → 2 → 3",
        18,
        fill=MUTED,
        mono=True,
        anchor="mm",
    )
    rounded_rect(draw, (1350, 814, 1810, 890), fill=SURFACE, outline=BORDER, width=2, radius=12)
    text(
        draw,
        (1580, 852),
        "stops with the latest typed error",
        18,
        fill=MUTED,
        mono=True,
        anchor="mm",
    )
    composite_scene(base, layer, visibility)


def finale_scene(base: Image.Image, local_time: float, duration: float) -> None:
    visibility = scene_visibility(local_time, duration + 0.6)
    scale = 0.94 + 0.06 * ease(local_time / 1.0)
    layer, draw, _ = scene_layer(visibility)
    draw_site_header(draw)

    logo_size = round(130 * scale)
    logo(draw, WIDTH / 2 - logo_size / 2, 218, logo_size)
    text(draw, (WIDTH / 2, 416), "better-result 3.0", 92, anchor="ma")
    text(draw, (WIDTH / 2, 545), "Expected failures, explicitly handled.", 40, fill=MUTED, anchor="ma")

    rounded_rect(draw, (WIDTH / 2 - 390, 668, WIDTH / 2 + 390, 748), fill=SURFACE, outline=BORDER, width=2, radius=14)
    text(draw, (WIDTH / 2, 708), "npm install better-result@latest", 31, mono=True, anchor="mm")
    badge_width = badge(draw, WIDTH / 2 - 141, 805, "better-result.dev", accent=True)
    if badge_width:
        pass
    composite_scene(base, layer, visibility)


SCENES = (
    (0.0, 5.0, intro_scene),
    (5.0, 10.3, tagged_error_scene),
    (10.3, 15.6, matching_scene),
    (15.6, 21.2, codec_scene),
    (21.2, 26.7, collections_scene),
    (26.7, 32.2, retry_scene),
    (32.2, DURATION_SECONDS, finale_scene),
)


def render_frame(frame_number: int) -> Image.Image:
    time = frame_number / FPS
    frame = Image.new("RGBA", (OUTPUT_WIDTH, OUTPUT_HEIGHT), BACKGROUND)
    draw_grid(frame, time)

    for start, end, renderer in SCENES:
        if start <= time < end:
            renderer(frame, time - start, end - start)
            break

    draw = ScaledDraw(frame)
    draw_progress(draw, time)
    return frame.convert("RGB")


def render_video(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_command = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "warning",
        "-f",
        "rawvideo",
        "-pixel_format",
        "rgb24",
        "-video_size",
        f"{OUTPUT_WIDTH}x{OUTPUT_HEIGHT}",
        "-framerate",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    process = subprocess.Popen(ffmpeg_command, stdin=subprocess.PIPE)
    if process.stdin is None:
        raise RuntimeError("Could not open ffmpeg input stream")

    frame_count = FPS * DURATION_SECONDS
    try:
        for frame_number in range(frame_count):
            process.stdin.write(render_frame(frame_number).tobytes())
            if frame_number % FPS == 0:
                print(
                    f"Rendering {frame_number // FPS:02d}/{DURATION_SECONDS}s",
                    file=sys.stderr,
                )
    finally:
        process.stdin.close()

    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with status {return_code}")

    print(f"Rendered {output_path}", file=sys.stderr)


if __name__ == "__main__":
    destination = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUTPUT
    render_video(destination)
