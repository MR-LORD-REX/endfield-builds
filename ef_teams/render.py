from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw

from .models import CharacterGuide, CharacterWithGuide, GearRecommendation, WeaponRecommendation
from .utils import (
    ACCENT_CYAN,
    AUTHOR_NAME,
    AUTHOR_URL,
    BG_DARK,
    BG_PANEL_DARK,
    BORDER,
    CON_COLOR,
    OPERATOR_RARITY,
    PRO_COLOR,
    RARITY_BOX,
    RARITY_FILL,
    RARITY_OUTLINE,
    TEXT_DARK,
    TEXT_LIGHT,
    TEXT_MUTED,
    TIER_COLORS,
    draw_asset_rarity_stars,
    draw_corner_brackets,
    draw_panel,
    draw_section_header,
    draw_wrapped_bullets,
    fetch_image,
    fetch_image_raw,
    fit_image_cover,
    get_font,
    paste_icon_with_frame,
    placeholder_icon,
    text_size,
    truncate_text,
    wrap_text,
)

WEAPON_BG = (22, 24, 32, 255)
WEAPON_ROW = (30, 33, 44, 255)
WEAPON_ROW_ALT = (26, 28, 38, 255)
WEAPON_ROW_TOP = (42, 38, 30, 255)
WEAPON_GOLD = RARITY_FILL[6]
WEAPON_HEADER_TEXT = (105, 112, 128, 255)

CARD_W = 1080
CARD_H = 1940
MARGIN = 24
INNER_W = CARD_W - MARGIN * 2
SPLASH_HEIGHT = 400
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
RENDER_CONCURRENCY = 8
IMAGE_FETCH_CONCURRENCY = 32


@dataclass(frozen=True)
class ImageRequest:
    url: str | None
    size: tuple[int, int]
    rarity: int = 4


def splash_display_size() -> tuple[int, int]:
    """Display size for the left splash panel (matches _draw_splash layout)."""
    return INNER_W // 2 - 12, SPLASH_HEIGHT - 12


class ImageCache:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self._cache: dict[tuple[str | None, int, int], Image.Image] = {}
        self._splash_cache: dict[str, Image.Image] = {}
        self._sem = asyncio.Semaphore(IMAGE_FETCH_CONCURRENCY)

    def _key(self, url: str | None, size: tuple[int, int]) -> tuple[str | None, int, int]:
        return (url, size[0], size[1])

    async def _fetch_splash(self, url: str) -> None:
        if url in self._splash_cache:
            return
        async with self._sem:
            try:
                self._splash_cache[url] = await fetch_image_raw(self.session, url)
            except (ValueError, aiohttp.ClientError, OSError):
                self._splash_cache[url] = placeholder_icon(splash_display_size(), 6)

    async def _fetch_one(self, request: ImageRequest) -> None:
        key = self._key(request.url, request.size)
        if key in self._cache:
            return
        if not request.url:
            self._cache[key] = placeholder_icon(request.size, request.rarity)
            return
        async with self._sem:
            try:
                self._cache[key] = await fetch_image(self.session, request.url, request.size)
            except (ValueError, aiohttp.ClientError, OSError):
                self._cache[key] = placeholder_icon(request.size, request.rarity)

    async def prefetch(
        self,
        requests: list[ImageRequest],
        splash_urls: list[str] | None = None,
    ) -> None:
        unique = {self._key(r.url, r.size): r for r in requests}
        splash_tasks = [
            self._fetch_splash(url)
            for url in dict.fromkeys(splash_urls or [])
            if url
        ]
        await asyncio.gather(
            *splash_tasks,
            *(self._fetch_one(r) for r in unique.values()),
        )

    def get_sync(self, url: str | None, size: tuple[int, int], rarity: int = 4) -> Image.Image:
        key = self._key(url, size)
        if key not in self._cache:
            self._cache[key] = placeholder_icon(size, rarity)
        return self._cache[key]

    def get_splash_sync(
        self,
        url: str | None,
        display_size: tuple[int, int],
        rarity: int = 6,
    ) -> Image.Image:
        if not url:
            return placeholder_icon(display_size, rarity)
        raw = self._splash_cache.get(url)
        if raw is None:
            return placeholder_icon(display_size, rarity)
        return fit_image_cover(raw, display_size)


def collect_image_requests(guide: CharacterGuide) -> list[ImageRequest]:
    requests: list[ImageRequest] = []

    for weapon in guide.weapons[:5]:
        option = weapon.options[0] if weapon.options else None
        rarity = option.rarity if option and option.rarity else 4
        requests.append(ImageRequest(option.icon_url if option else None, (36, 36), rarity))

    for gear in guide.gears[:3]:
        option = gear.options[0] if gear.options else None
        rarity = option.rarity if option and option.rarity else 5
        requests.append(ImageRequest(option.icon_url if option else None, (46, 46), rarity))
        for piece in gear.pieces[:4]:
            requests.append(ImageRequest(piece.icon_url, (34, 34), 4))

    for team in guide.teams[:4]:
        for member in team.members[:4]:
            requests.append(ImageRequest(member.icon_url, (50, 50), 5))

    for syn in guide.senergies[:7]:
        requests.append(ImageRequest(syn.icon_url, (56, 56), 5))
        if syn.element_icon:
            requests.append(ImageRequest(syn.element_icon, (20, 20), 4))

    return requests


class CharacterCardRenderer:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.cache = ImageCache(session)

    async def render(self, entry: CharacterWithGuide) -> Image.Image:
        if not entry.guide:
            raise ValueError(f"No guide data for {entry.name}")

        guide = entry.guide
        splash_urls = [guide.char_splash] if guide.char_splash else []
        await self.cache.prefetch(collect_image_requests(guide), splash_urls)
        canvas = await asyncio.to_thread(self._build_canvas, entry)
        return canvas.convert("RGB")

    def _build_canvas(self, entry: CharacterWithGuide) -> Image.Image:
        guide = entry.guide
        assert guide is not None

        canvas = Image.new("RGBA", (CARD_W, CARD_H), BG_DARK)
        draw = ImageDraw.Draw(canvas)
        self._draw_background_grid(draw)

        y = MARGIN
        y = self._draw_header(draw, canvas, entry, y)
        y = self._draw_splash(canvas, draw, guide, y)
        y = self._draw_weapons(canvas, draw, guide, y)
        y = self._draw_gears(canvas, draw, guide, y)
        y = self._draw_skill_orders(draw, guide, y)
        y = self._draw_teams(canvas, draw, guide, y)
        y = self._draw_synergies(canvas, draw, guide, y)
        self._draw_footer(draw, guide, y)
        return canvas

    def _draw_background_grid(self, draw: ImageDraw.ImageDraw) -> None:
        for x in range(0, CARD_W, 40):
            draw.line([(x, 0), (x, CARD_H)], fill=(40, 46, 56, 80), width=1)
        for y in range(0, CARD_H, 40):
            draw.line([(0, y), (CARD_W, y)], fill=(40, 46, 56, 80), width=1)

    def _draw_copyright(self, draw: ImageDraw.ImageDraw, y: int) -> int:
        font = get_font(13)
        prefix = f"© {AUTHOR_NAME}  "
        link = AUTHOR_URL.replace("https://", "")
        draw.text((MARGIN, y), prefix, fill=TEXT_MUTED, font=font)
        pw, _ = text_size(draw, prefix, font)
        draw.text((MARGIN + pw, y), link, fill=ACCENT_CYAN, font=font)
        return y + 22

    def _draw_header(
        self,
        draw: ImageDraw.ImageDraw,
        canvas: Image.Image,
        entry: CharacterWithGuide,
        y: int,
    ) -> int:
        y = self._draw_copyright(draw, y)

        font_logo = get_font(22)
        font_name = get_font(52)
        font_sub = get_font(18)

        draw.text((MARGIN, y), "ARKNIGHTS", fill=TEXT_MUTED, font=font_logo)
        draw.text((MARGIN + 180, y), "ENDFIELD", fill=ACCENT_CYAN, font=font_logo)

        rarity = OPERATOR_RARITY.get(entry.name, 6)
        stars = draw_asset_rarity_stars(rarity, rarity=rarity, star_size=22, gap=4)
        canvas.paste(stars, (CARD_W - MARGIN - stars.width, y), stars)

        y += 36
        draw.text((MARGIN, y), entry.name.upper(), fill=TEXT_LIGHT, font=font_name)
        y += 58
        draw.text((MARGIN, y), f"BUILD GUIDE  ·  {entry.slug}", fill=TEXT_MUTED, font=font_sub)
        draw.line([(MARGIN, y + 28), (CARD_W - MARGIN, y + 28)], fill=ACCENT_CYAN, width=2)
        return y + 40

    def _draw_splash(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        guide: CharacterGuide,
        y: int,
    ) -> int:
        art_w = INNER_W // 2
        outer_box = (MARGIN, y, CARD_W - MARGIN, y + SPLASH_HEIGHT)
        draw.rectangle(outer_box, fill=BG_PANEL_DARK, outline=BORDER, width=2)

        art_box = (MARGIN + 4, y + 4, MARGIN + art_w - 4, y + SPLASH_HEIGHT - 4)
        info_box = (MARGIN + art_w + 4, y + 4, CARD_W - MARGIN - 4, y + SPLASH_HEIGHT - 4)
        draw.rectangle(art_box, fill=(18, 20, 28, 255), outline=BORDER, width=1)
        draw.rectangle(info_box, fill=(28, 31, 40, 255), outline=BORDER, width=1)

        display_w, display_h = splash_display_size()
        splash = self.cache.get_splash_sync(guide.char_splash, (display_w, display_h), 6)
        canvas.paste(splash, (art_box[0] + 2, art_box[1] + 2), splash)
        draw_corner_brackets(draw, art_box)
        self._draw_character_info(draw, guide, info_box)

        return y + SPLASH_HEIGHT + 12

    def _draw_character_info(
        self,
        draw: ImageDraw.ImageDraw,
        guide: CharacterGuide,
        box: tuple[int, int, int, int],
    ) -> None:
        x0, y0, x1, y1 = box
        pad = 12
        width = x1 - x0 - pad * 2
        cursor_y = y0 + pad

        label_font = get_font(13)
        value_font = get_font(14)
        body_font = get_font(13)

        draw.text((x0 + pad, cursor_y), "RATING", fill=ACCENT_CYAN, font=label_font)
        cursor_y += 20

        if guide.rating and any([guide.rating.rank, guide.rating.role, guide.rating.mode]):
            rank = guide.rating.rank or "—"
            tier_color = TIER_COLORS.get(rank, TEXT_LIGHT)
            badge_w, badge_h = 52, 28
            draw.rectangle(
                (x0 + pad, cursor_y, x0 + pad + badge_w, cursor_y + badge_h),
                fill=RARITY_BOX.get(6, (40, 40, 40, 255)),
                outline=tier_color,
                width=2,
            )
            rank_font = get_font(16)
            rtw, rth = text_size(draw, rank, rank_font)
            draw.text(
                (x0 + pad + (badge_w - rtw) // 2, cursor_y + (badge_h - rth) // 2 - 1),
                rank,
                fill=tier_color,
                font=rank_font,
            )

            meta_x = x0 + pad + badge_w + 10
            if guide.rating.role:
                draw.text((meta_x, cursor_y + 2), guide.rating.role, fill=TEXT_LIGHT, font=value_font)
            if guide.rating.mode:
                mode = truncate_text(draw, guide.rating.mode, body_font, width - badge_w - 14)
                draw.text((meta_x, cursor_y + 20), mode, fill=TEXT_MUTED, font=body_font)
            cursor_y += badge_h + 10
        else:
            draw.text((x0 + pad, cursor_y), "No rating data", fill=TEXT_MUTED, font=body_font)
            cursor_y += 24

        draw.line([(x0 + pad, cursor_y), (x1 - pad, cursor_y)], fill=BORDER, width=1)
        cursor_y += 10

        if guide.analysis:
            remaining = y1 - cursor_y - pad
            pros_height = int(remaining * 0.58)
            cons_height = remaining - pros_height - 24

            draw.text((x0 + pad, cursor_y), "PROS", fill=PRO_COLOR, font=label_font)
            cursor_y += 20
            cursor_y = draw_wrapped_bullets(
                draw, x0 + pad, cursor_y, width, pros_height,
                guide.analysis.pros, body_font, PRO_COLOR, bullet="+", line_height=16, max_items=5,
            )
            cursor_y += 10
            draw.text((x0 + pad, cursor_y), "CONS", fill=CON_COLOR, font=label_font)
            cursor_y += 20
            draw_wrapped_bullets(
                draw, x0 + pad, cursor_y, width, cons_height,
                guide.analysis.cons, body_font, CON_COLOR, bullet="−", line_height=16, max_items=4,
            )

    def _draw_weapons(self, canvas: Image.Image, draw: ImageDraw.ImageDraw, guide: CharacterGuide, y: int) -> int:
        header_h = 36
        y = draw_section_header(draw, MARGIN, y, INNER_W, header_h, "WEAPON", get_font(20))

        weapons = guide.weapons[:5]
        row_h = 54
        table_header_h = 26
        section_h = table_header_h + row_h * max(len(weapons), 1) + 8
        draw.rectangle((MARGIN, y, CARD_W - MARGIN, y + section_h), fill=WEAPON_BG, outline=BORDER, width=2)

        if not weapons:
            draw.text((MARGIN + 16, y + 16), "No weapon data", fill=TEXT_MUTED, font=get_font(18))
            return y + section_h + 12

        col_x = {
            "weapon": MARGIN + 12,
            "rarity": MARGIN + 430,
            "pot": MARGIN + 560,
            "solo": MARGIN + 720,
            "team": MARGIN + 880,
        }
        header_font = get_font(13)
        for key, label in [
            ("weapon", "Weapon"), ("rarity", "Rarity"), ("pot", "Pot"),
            ("solo", "Solo %"), ("team", "Team %"),
        ]:
            draw.text((col_x[key], y + 6), label, fill=WEAPON_HEADER_TEXT, font=header_font)
        draw.line(
            [(MARGIN + 8, y + table_header_h), (CARD_W - MARGIN - 8, y + table_header_h)],
            fill=BORDER, width=1,
        )

        for i, weapon in enumerate(weapons):
            row_y = y + table_header_h + i * row_h
            row_bg = WEAPON_ROW_TOP if i == 0 else (WEAPON_ROW if i % 2 == 0 else WEAPON_ROW_ALT)
            draw.rectangle(
                (MARGIN + 6, row_y + 2, CARD_W - MARGIN - 6, row_y + row_h - 2),
                fill=row_bg,
            )
            self._draw_weapon_row(canvas, draw, weapon, row_y, row_h, col_x, i == 0)

        return y + section_h + 12

    def _draw_weapon_row(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        weapon: WeaponRecommendation,
        row_y: int,
        row_h: int,
        col_x: dict[str, int],
        is_top: bool,
    ) -> None:
        option = weapon.options[0] if weapon.options else None
        rarity = option.rarity if option and option.rarity else 4

        rank_size = (30, 30)
        icon_size = (44, 44)
        cy = row_y + (row_h - icon_size[1]) // 2
        rx = col_x["weapon"]

        rank_img = Image.new("RGBA", rank_size, RARITY_BOX[rarity])
        rank_draw = ImageDraw.Draw(rank_img)
        rank_draw.rectangle([(0, 0), (rank_size[0] - 1, rank_size[1] - 1)], outline=RARITY_OUTLINE[rarity], width=2)
        rank_font = get_font(14)
        rank_label = f"#{weapon.rank}"
        rtw, rth = text_size(rank_draw, rank_label, rank_font)
        rank_draw.text(
            ((rank_size[0] - rtw) // 2, (rank_size[1] - rth) // 2 - 1),
            rank_label, fill=TEXT_LIGHT, font=rank_font,
        )
        canvas.paste(rank_img, (rx, cy + 7), rank_img)

        icon = self.cache.get_sync(option.icon_url if option else None, (36, 36), rarity)
        paste_icon_with_frame(canvas, icon, (rx + rank_size[0] + 8, cy), icon_size, rarity)

        name_font = get_font(17 if is_top else 16)
        name_x = rx + rank_size[0] + icon_size[0] + 18
        name = truncate_text(draw, option.name if option else "Unknown", name_font, col_x["rarity"] - name_x - 12)
        draw.text((name_x, cy + 12), name, fill=WEAPON_GOLD if is_top else TEXT_LIGHT, font=name_font)

        if option and option.rarity:
            stars = draw_asset_rarity_stars(option.rarity, rarity=option.rarity, star_size=16, gap=3)
            canvas.paste(stars, (col_x["rarity"], cy + 13), stars)

        pot = option.potential if option and option.potential else "—"
        draw.text((col_x["pot"], cy + 14), pot, fill=TEXT_MUTED, font=get_font(14))
        stat_font = get_font(15 if is_top else 14)
        draw.text((col_x["solo"], cy + 14), weapon.solo or "—", fill=WEAPON_GOLD if is_top else TEXT_LIGHT, font=stat_font)
        draw.text((col_x["team"], cy + 14), weapon.team or "—", fill=TEXT_MUTED, font=stat_font)

    def _draw_gears(self, canvas: Image.Image, draw: ImageDraw.ImageDraw, guide: CharacterGuide, y: int) -> int:
        gears = guide.gears[:3]
        if not gears:
            return y

        labels = ["BEST GEAR", "ALT GEAR #2", "ALT GEAR #3"]
        col_w = (INNER_W - 16) // 3
        section_h = 360
        row_y = y

        for idx, gear in enumerate(gears):
            x = MARGIN + idx * (col_w + 8)
            label = labels[idx] if idx < len(labels) else f"GEAR #{gear.rank}"
            y_header = draw_section_header(draw, x, row_y, col_w, 32, label, get_font(15))
            draw_panel(draw, (x, y_header, x + col_w, row_y + section_h))
            self._draw_gear_column(canvas, draw, gear, x, y_header, col_w, section_h)

        return row_y + section_h + 12

    def _draw_gear_column(
        self,
        canvas: Image.Image,
        draw: ImageDraw.ImageDraw,
        gear: GearRecommendation,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> None:
        pad = 10
        cursor_y = y + pad
        option = gear.options[0] if gear.options else None
        icon_size = (52, 52)
        rarity = option.rarity if option and option.rarity else 5

        icon = self.cache.get_sync(option.icon_url if option else None, (46, 46), rarity)
        paste_icon_with_frame(canvas, icon, (x + pad, cursor_y), icon_size, rarity)

        name_font = get_font(14)
        draw.text((x + pad + icon_size[0] + 8, cursor_y + 6), option.name if option else "Custom", fill=TEXT_DARK, font=name_font)
        stats = [f"Solo {gear.solo}" if gear.solo else None, f"Team {gear.team}" if gear.team else None]
        stats = [s for s in stats if s]
        if stats:
            draw.text((x + pad + icon_size[0] + 8, cursor_y + 28), " · ".join(stats), fill=TEXT_MUTED, font=get_font(12))
        cursor_y += icon_size[1] + 12

        piece_size = (40, 40)
        piece_font = get_font(11)
        for piece in gear.pieces[:4]:
            picon = self.cache.get_sync(piece.icon_url, (34, 34), 4)
            paste_icon_with_frame(canvas, picon, (x + pad, cursor_y), piece_size, 4)
            draw.text((x + pad + piece_size[0] + 6, cursor_y + 2), piece.type or "Gear", fill=TEXT_MUTED, font=piece_font)
            pname = truncate_text(draw, piece.name or "—", piece_font, width - pad * 2 - piece_size[0] - 10)
            draw.text((x + pad + piece_size[0] + 6, cursor_y + 18), pname, fill=TEXT_DARK, font=piece_font)
            cursor_y += piece_size[1] + 6

        if gear.comments:
            comment_font = get_font(10)
            for line in wrap_text(draw, gear.comments, comment_font, width - pad * 2)[:3]:
                draw.text((x + pad, cursor_y), line, fill=TEXT_MUTED, font=comment_font)
                cursor_y += 13

    def _draw_skill_orders(self, draw: ImageDraw.ImageDraw, guide: CharacterGuide, y: int) -> int:
        y = draw_section_header(draw, MARGIN, y, INNER_W, 32, "SKILL PRIORITY", get_font(18))
        box_h = 90
        draw_panel(draw, (MARGIN, y, CARD_W - MARGIN, y + box_h))
        font = get_font(16)
        cursor_y = y + 12
        for i, order in enumerate(guide.skill_orders[:2]):
            prefix = f"Build {i + 1}: "
            draw.text((MARGIN + 14, cursor_y), prefix, fill=ACCENT_CYAN, font=font)
            pw, _ = text_size(draw, prefix, font)
            draw.text((MARGIN + 14 + pw, cursor_y), order, fill=TEXT_DARK, font=font)
            cursor_y += 34
        return y + box_h + 12

    def _draw_teams(self, canvas: Image.Image, draw: ImageDraw.ImageDraw, guide: CharacterGuide, y: int) -> int:
        y = draw_section_header(draw, MARGIN, y, INNER_W, 32, "TEAM COMP", get_font(18))
        teams = guide.teams[:4]
        cell_h, cell_w = 130, INNER_W // 2
        section_h = 2 * cell_h
        draw_panel(draw, (MARGIN, y, CARD_W - MARGIN, y + section_h))

        avatar_size = (56, 56)
        name_font, title_font = get_font(12), get_font(14)
        for i, team in enumerate(teams):
            row, col = divmod(i, 2)
            cx = MARGIN + col * cell_w + 12
            cy = y + row * cell_h + 10
            draw.text((cx, cy), team.name or f"Team {i + 1}", fill=TEXT_DARK, font=title_font)
            member_x, member_y = cx, cy + 24
            for member in team.members[:4]:
                icon = self.cache.get_sync(member.icon_url, (50, 50), 5)
                paste_icon_with_frame(canvas, icon, (member_x, member_y), avatar_size, 5)
                mname = truncate_text(draw, member.name or "?", name_font, avatar_size[0])
                tw, _ = text_size(draw, mname, name_font)
                draw.text(
                    (member_x + (avatar_size[0] - tw) // 2, member_y + avatar_size[1] + 2),
                    mname, fill=TEXT_MUTED, font=name_font,
                )
                member_x += avatar_size[0] + 10
        return y + section_h + 12

    def _draw_synergies(self, canvas: Image.Image, draw: ImageDraw.ImageDraw, guide: CharacterGuide, y: int) -> int:
        y = draw_section_header(draw, MARGIN, y, INNER_W, 32, "SYNERGY", get_font(18))
        senergies = guide.senergies[:7]
        section_h = 120
        draw_panel(draw, (MARGIN, y, CARD_W - MARGIN, y + section_h))

        icon_size = (64, 64)
        elem_size = (20, 20)
        gap = 12
        total_w = len(senergies) * (icon_size[0] + gap) - gap
        start_x = MARGIN + max((INNER_W - total_w) // 2, 12)
        name_font, elem_font = get_font(11), get_font(10)

        for i, syn in enumerate(senergies):
            x = start_x + i * (icon_size[0] + gap)
            icon = self.cache.get_sync(syn.icon_url, (56, 56), 5)
            paste_icon_with_frame(canvas, icon, (x, y + 14), icon_size, 5)
            if syn.element_icon:
                elem = self.cache.get_sync(syn.element_icon, elem_size, 4)
                canvas.paste(elem, (x + icon_size[0] - elem_size[0], y + 14), elem)
            sname = truncate_text(draw, syn.name or "?", name_font, icon_size[0] + 8)
            tw, _ = text_size(draw, sname, name_font)
            draw.text((x + (icon_size[0] - tw) // 2, y + 82), sname, fill=TEXT_DARK, font=name_font)
            if syn.element:
                ew, _ = text_size(draw, syn.element, elem_font)
                draw.text((x + (icon_size[0] - ew) // 2, y + 98), syn.element, fill=ACCENT_CYAN, font=elem_font)
        return y + section_h + 12

    def _draw_footer(self, draw: ImageDraw.ImageDraw, guide: CharacterGuide, y: int) -> None:
        font = get_font(14)
        text = f"Data source: Prydwen.gg  ·  Updated {guide.last_updated}"
        tw, th = text_size(draw, text, font)
        draw.text(((CARD_W - tw) // 2, CARD_H - MARGIN - th), text, fill=TEXT_MUTED, font=font)


async def render_character_card(
    entry: CharacterWithGuide,
    session: aiohttp.ClientSession,
) -> Image.Image:
    renderer = CharacterCardRenderer(session)
    return await renderer.render(entry)


async def save_character_card(
    entry: CharacterWithGuide,
    session: aiohttp.ClientSession,
    output_path: str | Path,
) -> Path:
    image = await render_character_card(entry, session)
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(image.save, path, quality=95)
    return path
