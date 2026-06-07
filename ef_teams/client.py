import asyncio
import json
from pathlib import Path

import aiohttp

from .models import CharacterWithGuide
from .render import RENDER_CONCURRENCY, save_character_card

from .api import fetch_character_guide , fetch_characters

DEFAULT_GUIDES_PATH = Path(__file__).parent / "assets" / "metadata" / "character_guides.json"
characters_path = Path(__file__).parent / "assets" / "metadata" / "characters.json"
file_map=Path(__file__).parent / "assets" / "metadata" / "file_map.json"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


class GuideClient:
    def __init__(
        self,
        guides_path: Path | str = DEFAULT_GUIDES_PATH,
        output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    ):
        self.guides_path = Path(guides_path)
        self.output_dir = Path(output_dir)
        self._guides: dict[str, CharacterWithGuide] | None = None

    def load(self) -> dict[str, CharacterWithGuide]:
        if self._guides is not None:
            return self._guides

        with open(self.guides_path, encoding="utf-8") as f:
            raw = json.load(f)

        self._guides = {
            char_id: CharacterWithGuide.model_validate(entry)
            for char_id, entry in raw.items()
        }
        return self._guides

    def get(self, char_id: str) -> CharacterWithGuide | None:
        return self.load().get(char_id)

    def get_by_slug(self, slug: str) -> CharacterWithGuide | None:
        for entry in self.load().values():
            if entry.slug == slug:
                return entry
        return None

    def list_characters(self) -> list[tuple[str, CharacterWithGuide]]:
        return list(self.load().items())
    
    async def _fetch_guides(self) -> None:
        char_path = characters_path
        g_p = DEFAULT_GUIDES_PATH
        all_guides: dict[str, dict] = {}
        with open(char_path, encoding="utf-8") as f:
            characters = json.load(f)
            for char_id, char_info in characters.items():
                slug = char_info.get("slug")
                if slug:
                    print(f"Fetching guide for {char_info.get('name')} ({slug})...")
                    guide = await fetch_character_guide(slug)
                    entry = CharacterWithGuide(
                        name=char_info.get("name"),
                        slug=slug,
                        guide=guide,
                    )
                    all_guides[char_id] = entry.model_dump(mode="json", exclude_none=True)
                else:
                    print(f"No slug found for {char_info.get('name')} (ID: {char_id})")
                await asyncio.sleep(1)
        with open(g_p, "w", encoding="utf-8") as f:
            json.dump(all_guides, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(all_guides)} guides to {g_p}")
    
    async def update_guides(self):
        await fetch_characters()
        await self._fetch_guides()
        with open(characters_path, encoding="utf-8") as f:
            characters = json.load(f)
            with open(file_map, "w", encoding="utf-8") as fm:
                map_data = {}
                for char_id, char_info in characters.items():
                    name = char_info.get("name")
                    slug = char_info.get("slug")
                    if slug:
                        map_data[slug] = {
                            "char_id": char_id,
                            "name": name,
                            "raw_url": f"https://raw.githubusercontent.com/MR-LORD-REX/endfield-builds/main/output/{slug}.png",
                            "image_url": f"https://github.com/MR-LORD-REX/endfield-builds/blob/main/output/{slug}.png",
                            "icon_url": f"https://cdn.prydwen.gg/images/arknights-endfield/characters/{slug}_icon.webp"
                        }
                json.dump(map_data, fm, ensure_ascii=False, indent=2)
            print(f"Updated file map with {len(map_data)} entries")
            

    async def render_character(
        self,
        char_id: str,
        output_path: Path | str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> Path:
        entry = self.get(char_id)
        if not entry or not entry.guide:
            raise ValueError(f"Character '{char_id}' not found or has no guide data")

        if output_path is None:
            output_path = self.output_dir / f"{entry.slug}.png"

        if session is not None:
            return await save_character_card(entry, session, output_path)

        async with aiohttp.ClientSession() as owned_session:
            return await save_character_card(entry, owned_session, output_path)

    async def render_all(
        self,
        output_dir: Path | str | None = None,
        concurrency: int = RENDER_CONCURRENCY,
    ) -> list[Path]:
        out = Path(output_dir) if output_dir else self.output_dir
        out.mkdir(parents=True, exist_ok=True)

        seen_slugs: set[str] = set()
        entries: list[CharacterWithGuide] = []
        for _, entry in self.list_characters():
            if not entry.guide or entry.slug in seen_slugs:
                continue
            seen_slugs.add(entry.slug)
            entries.append(entry)

        sem = asyncio.Semaphore(concurrency)
        saved: list[Path] = []

        async with aiohttp.ClientSession() as session:
            async def render_one(entry: CharacterWithGuide) -> Path:
                async with sem:
                    return await save_character_card(entry, session, out / f"{entry.slug}.png")

            saved = await asyncio.gather(*(render_one(entry) for entry in entries))
        return list(saved)
