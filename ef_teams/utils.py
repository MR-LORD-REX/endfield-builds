import math
from io import BytesIO
from pathlib import Path
from typing import Literal, Tuple

import aiohttp
from PIL import Image, ImageDraw, ImageFont

font_path = Path(__file__).parent / "assets" / "fonts" / "EF_fonts.ttf"
star_asset_path = Path(__file__).parent / "assets" / "card_assets" / "star.png"
AUTHOR_NAME = "MR-LORD-REX"
AUTHOR_URL = "https://github.com/MR-LORD-REX/"
FONT_FALLBACKS = [
    font_path,
    Path("C:/Windows/Fonts/segoeuib.ttf"),
    Path("C:/Windows/Fonts/arialbd.ttf"),
]

# Card palette — sci-fi Endfield-inspired
BG_DARK = (32, 36, 44, 255)
BG_PANEL = (245, 247, 250, 255)
BG_PANEL_DARK = (52, 58, 72, 255)
ACCENT_CYAN = (0, 212, 255, 255)
ACCENT_ORANGE = (255, 140, 66, 255)
ACCENT_LIME = (200, 230, 0, 255)
TEXT_DARK = (20, 24, 32, 255)
TEXT_LIGHT = (235, 240, 248, 255)
TEXT_MUTED = (130, 140, 155, 255)
PRO_COLOR = (86, 201, 120, 255)
CON_COLOR = (255, 110, 100, 255)
BORDER = (70, 80, 100, 255)

RARITY_OUTLINE: dict[int, tuple[int, int, int, int]] = {
    1: (180, 180, 180, 255),
    2: (86, 201, 120, 255),
    3: (73, 150, 255, 255),
    4: (177, 107, 255, 255),
    5: (255, 205, 74, 255),
    6: (246, 161, 43, 255),
}

RARITY_FILL: dict[int, tuple[int, int, int, int]] = {
    1: (110, 110, 110, 255),
    2: (45, 135, 70, 255),
    3: (45, 105, 200, 255),
    4: (120, 70, 190, 255),
    5: (195, 150, 25, 255),
    6: (246, 161, 43, 255),
}

RARITY_BOX: dict[int, tuple[int, int, int, int]] = {
    1: (55, 55, 55, 255),
    2: (20, 70, 35, 255),
    3: (18, 50, 105, 255),
    4: (55, 25, 100, 255),
    5: (100, 75, 0, 255),
    6: (101, 71, 0, 255),
}

TIER_COLORS: dict[str, tuple[int, int, int, int]] = {
    "T0": RARITY_FILL[6],
    "T1": RARITY_FILL[6],
    "T2": RARITY_FILL[5],
    "T3": RARITY_FILL[4],
    "T4": RARITY_FILL[3],
}

OPERATOR_RARITY: dict[str, int] = {
    "Endministrator": 6,
    "Lifeng": 6,
    "Pogranichnik": 6,
    "Ardelia": 6,
    "Laevatain": 6,
    "Gilberta": 6,
    "Yvonne": 6,
    "Last Rite": 6,
    "Ember": 6,
    "Rossi": 6,
    "Chen Qianyu": 5,
    "Da Pan": 5,
    "Snowshine": 5,
    "Wulfgard": 5,
    "Perlica": 5,
    "Arclight": 5,
    "Avywenna": 5,
    "Alesh": 5,
    "Xaihi": 5,
    "Akekuri": 4,
    "Estella": 4,
    "Catcher": 4,
    "Fluorite": 4,
    "Antal": 4,
    "Tangtang": 6,
    "Mifu": 4,
    "Zhuang Fangyi": 5,
}


HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://www.prydwen.gg/",
}


async def fetch_image_raw(session: aiohttp.ClientSession, url: str) -> Image.Image:
    """Fetch an image at its native resolution."""
    async with session.get(url, headers=HTTP_HEADERS) as response:
        if response.status != 200:
            raise ValueError(f"Failed to fetch image from {url}: {response.status}")
        data = await response.read()
        return Image.open(BytesIO(data)).convert("RGBA")


async def fetch_image(
    session: aiohttp.ClientSession,
    url: str,
    size: tuple[int, int] = (160, 160),
) -> Image.Image:
    """Fetch an image from a URL and resize it to the specified size."""
    image = await fetch_image_raw(session, url)
    return image.resize(size, Image.Resampling.LANCZOS)


def get_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load the custom font at the specified size, with system fallbacks."""
    for path in FONT_FALLBACKS:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        test = f"{current} {word}"
        if text_size(draw, test, font)[0] <= max_width:
            current = test
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def draw_wrapped_bullets(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    max_height: int,
    items: list[str],
    font: ImageFont.ImageFont,
    color: tuple[int, int, int, int],
    bullet: str = "•",
    line_height: int = 14,
    max_items: int = 6,
) -> int:
    """Draw a compact bullet list and return the final y position."""
    cursor_y = y
    bottom = y + max_height
    for item in items[:max_items]:
        lines = wrap_text(draw, f"{bullet} {item}", font, width)
        for line in lines:
            if cursor_y + line_height > bottom:
                return cursor_y
            draw.text((x, cursor_y), line, fill=color, font=font)
            cursor_y += line_height
    return cursor_y


def truncate_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
) -> str:
    if text_size(draw, text, font)[0] <= max_width:
        return text
    ellipsis = "..."
    while len(text) > 1:
        text = text[:-1]
        if text_size(draw, text + ellipsis, font)[0] <= max_width:
            return text + ellipsis
    return ellipsis


def draw_gradient_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color_start: tuple[int, int, int, int],
    color_end: tuple[int, int, int, int],
    horizontal: bool = True,
) -> None:
    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    steps = max(width if horizontal else height, 1)
    for i in range(steps):
        t = i / max(steps - 1, 1)
        color = tuple(
            int(color_start[c] + (color_end[c] - color_start[c]) * t)
            for c in range(4)
        )
        if horizontal:
            draw.line([(x0 + i, y0), (x0 + i, y1)], fill=color)
        else:
            draw.line([(x0, y0 + i), (x1, y0 + i)], fill=color)


def draw_star(
    size: int,
    color: tuple[int, int, int, int],
    points: int = 4,
) -> Image.Image:
    """Draw a filled PIL placeholder star for rarity display."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    outer_r = size / 2 - 1
    inner_r = outer_r * 0.38
    vertices = points * 2
    coords: list[tuple[float, float]] = []
    for i in range(vertices):
        angle = math.pi / points * i - math.pi / 2
        r = outer_r if i % 2 == 0 else inner_r
        coords.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    draw.polygon(coords, fill=color)
    highlight = tuple(min(255, c + 40) for c in color[:3]) + (255,)
    draw.polygon(
        [
            (cx, cy - outer_r * 0.55),
            (cx + inner_r * 0.35, cy - inner_r * 0.2),
            (cx, cy),
            (cx - inner_r * 0.35, cy - inner_r * 0.2),
        ],
        fill=highlight,
    )
    return img


def fit_image_cover(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """Scale and center-crop an image to fill the target box."""
    target_w, target_h = size
    src_w, src_h = img.size
    scale = max(target_w / src_w, target_h / src_h)
    new_w, new_h = int(src_w * scale), int(src_h * scale)
    resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


_star_tint_cache: dict[tuple[int, int, int, int, int], Image.Image] = {}


def tint_star_asset(
    size: int,
    color: tuple[int, int, int, int],
) -> Image.Image:
    """Tint the bundled star.png asset to a rarity color."""
    cache_key = (size, color[0], color[1], color[2], color[3])
    if cache_key in _star_tint_cache:
        return _star_tint_cache[cache_key].copy()

    base = Image.open(star_asset_path).convert("RGBA")
    base = base.resize((size, size), Image.Resampling.LANCZOS)
    tinted = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    src_px = base.load()
    dst_px = tinted.load()
    r, g, b, _ = color
    for y in range(size):
        for x in range(size):
            pr, pg, pb, pa = src_px[x, y]
            lum = max(pr, pg, pb)
            if lum > 24 and pa > 0:
                strength = lum / 255.0
                alpha = min(255, int(pa * strength))
                dst_px[x, y] = (int(r * strength), int(g * strength), int(b * strength), alpha)

    _star_tint_cache[cache_key] = tinted.copy()
    return tinted


def draw_asset_rarity_stars(
    count: int,
    rarity: int = 6,
    star_size: int = 18,
    gap: int = 3,
) -> Image.Image:
    """Build a row of rarity-colored stars using the bundled star asset."""
    count = max(1, min(count, 6))
    rarity = max(1, min(rarity, 6))
    color = RARITY_FILL[rarity]
    width = count * star_size + (count - 1) * gap
    row = Image.new("RGBA", (width, star_size), (0, 0, 0, 0))
    star = tint_star_asset(star_size, color)
    for i in range(count):
        row.paste(star, (i * (star_size + gap), 0), star)
    return row


def draw_rarity_pips(
    count: int,
    rarity: int = 6,
    pip_size: int = 14,
    gap: int = 3,
) -> Image.Image:
    """Build a row of rarity-colored square pips for weapon tables."""
    return draw_asset_rarity_stars(count, rarity, pip_size, gap)


def draw_rarity_stars(
    count: int,
    rarity: int = 6,
    star_size: int = 18,
    gap: int = 3,
) -> Image.Image:
    """Build a row of rarity-colored stars using the bundled star asset."""
    return draw_asset_rarity_stars(count, rarity, star_size, gap)


def draw_section_header(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    height: int,
    title: str,
    font: ImageFont.ImageFont,
) -> int:
    """Draw an orange-to-lime gradient section header bar."""
    draw_gradient_rect(draw, (x, y, x + width, y + height), ACCENT_ORANGE, ACCENT_LIME)
    draw.rectangle((x, y, x + width, y + height), outline=BORDER, width=1)
    tw, th = text_size(draw, title, font)
    draw.text((x + 14, y + (height - th) // 2), title, fill=TEXT_DARK, font=font)
    return y + height


def draw_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int, int] = BG_PANEL,
    border: tuple[int, int, int, int] = BORDER,
) -> None:
    draw.rectangle(box, fill=fill, outline=border, width=2)


def draw_corner_brackets(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int, int] = ACCENT_CYAN,
    length: int = 18,
    width: int = 2,
) -> None:
    x0, y0, x1, y1 = box
    corners = [
        [(x0, y0 + length), (x0, y0), (x0 + length, y0)],
        [(x1 - length, y0), (x1, y0), (x1, y0 + length)],
        [(x0, y1 - length), (x0, y1), (x0 + length, y1)],
        [(x1 - length, y1), (x1, y1), (x1, y1 - length)],
    ]
    for corner in corners:
        draw.line(corner, fill=color, width=width)


def get_weapon_holder(
    rarity: Literal[6, 5, 4, 3, 2, 1] = 6,
    type_: Literal["weapon", "index", "background"] = "weapon",
) -> Image.Image:
    """Get the weapon holder image based on rarity and type."""
    rarity = max(1, min(rarity, 6))  # type: ignore[arg-type]
    type_ = type_.lower()  # type: ignore[assignment]
    if type_ not in ["weapon", "index", "background"]:
        raise ValueError("type_ must be 'weapon', 'index', or 'background'")

    outline = RARITY_OUTLINE
    box = RARITY_BOX
    bg = {
        1: (110, 110, 110, 255),
        2: (45, 135, 70, 255),
        3: (45, 105, 200, 255),
        4: (120, 70, 190, 255),
        5: (195, 150, 25, 255),
        6: (167, 108, 13, 255),
    }
    if type_ == "weapon":
        size = (40, 40)
        new = Image.new("RGBA", size, box[rarity])
        d = ImageDraw.Draw(new)
        d.rectangle([(0, 0), size], outline=outline[rarity], width=2)
        return new
    if type_ == "index":
        size = (30, 40)
        new = Image.new("RGBA", size, box[rarity])
        d = ImageDraw.Draw(new)
        d.rectangle([(0, 0), size], outline=outline[rarity], width=2)
        return new
    size = (720, 40)
    return Image.new("RGBA", size, bg[rarity])


def fit_text_into_box(
    draw: ImageDraw.ImageDraw,
    text: str,
    font_path_: Path,
    box_width: int,
    box_height: int,
) -> Tuple[ImageFont.FreeTypeFont | ImageFont.ImageFont, int]:
    """Find the largest font size that allows the text to fit within the specified box."""
    font_size = 100
    while font_size > 0:
        font = ImageFont.truetype(str(font_path_), font_size) if font_path_.exists() else get_font(font_size)
        if text_size(draw, text, font)[1] <= box_height and text_size(draw, text, font)[0] <= box_width:
            break
        font_size -= 1
    lines = 1
    while True:
        font = ImageFont.truetype(str(font_path_), font_size) if font_path_.exists() else get_font(font_size)
        tw, th = text_size(draw, text, font)
        if tw <= box_width and th * lines <= box_height:
            break
        if tw > box_width:
            lines += 1
        else:
            font_size -= 1
    return font, lines


def paste_icon_with_frame(
    canvas: Image.Image,
    icon: Image.Image,
    pos: tuple[int, int],
    size: tuple[int, int],
    rarity: int | None = None,
) -> None:
    """Paste an icon centered inside a rarity-colored frame."""
    rarity = max(1, min(rarity or 4, 6))
    frame = Image.new("RGBA", size, RARITY_BOX[rarity])
    draw = ImageDraw.Draw(frame)
    draw.rectangle([(0, 0), (size[0] - 1, size[1] - 1)], outline=RARITY_OUTLINE[rarity], width=2)
    inner = (size[0] - 8, size[1] - 8)
    icon_fit = icon.resize(inner, Image.Resampling.LANCZOS)
    frame.paste(icon_fit, ((size[0] - inner[0]) // 2, (size[1] - inner[1]) // 2), icon_fit)
    canvas.paste(frame, pos, frame)


def placeholder_icon(size: tuple[int, int], rarity: int = 4) -> Image.Image:
    img = Image.new("RGBA", size, RARITY_BOX[rarity])
    draw = ImageDraw.Draw(img)
    draw.rectangle([(0, 0), (size[0] - 1, size[1] - 1)], outline=RARITY_OUTLINE[rarity], width=2)
    font = get_font(max(size[1] // 3, 10))
    tw, th = text_size(draw, "?", font)
    draw.text(((size[0] - tw) // 2, (size[1] - th) // 2), "?", fill=TEXT_LIGHT, font=font)
    return img
