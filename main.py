import asyncio
import json

from ef_teams.api import fetch_character_guide
from ef_teams.client import GuideClient
from ef_teams.models import CharacterWithGuide

CHARS_PATH = "ef_teams/assets/metadata/characters.json"
GUIDES_PATH = "ef_teams/assets/metadata/character_guides.json"


def show_menu() -> None:
    print("\n=== Endfield Character Guide Tools ===")
    print("1. Fetch guides from Prydwen")
    print("2. Render all character cards")
    print("3. Render a single character card")
    print("0. Exit")


async def fetch_guides() -> None:
    all_guides: dict[str, dict] = {}
    with open(CHARS_PATH, encoding="utf-8") as f:
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
    with open(GUIDES_PATH, "w", encoding="utf-8") as f:
        json.dump(all_guides, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_guides)} guides to {GUIDES_PATH}")


async def render_all_cards() -> None:
    client = GuideClient(guides_path=GUIDES_PATH)
    paths = await client.render_all()
    print(f"Rendered {len(paths)} character cards to {client.output_dir}")


async def render_single_card() -> None:
    client = GuideClient(guides_path=GUIDES_PATH)
    characters = [
        (char_id, entry)
        for char_id, entry in client.list_characters()
        if entry.guide
    ]
    if not characters:
        print("No character guides found. Run option 1 first.")
        return

    seen_slugs: set[str] = set()
    unique: list[tuple[str, CharacterWithGuide]] = []
    for char_id, entry in characters:
        if entry.slug in seen_slugs:
            continue
        seen_slugs.add(entry.slug)
        unique.append((char_id, entry))

    print("\nAvailable characters:")
    for i, (_, entry) in enumerate(unique, start=1):
        print(f"  {i}. {entry.name} ({entry.slug})")

    choice = input("\nEnter number or slug: ").strip()
    if not choice:
        print("Cancelled.")
        return

    char_id: str | None = None
    entry: CharacterWithGuide | None = None

    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(unique):
            char_id, entry = unique[index]
        else:
            print("Invalid number.")
            return
    else:
        entry = client.get_by_slug(choice)
        if entry:
            char_id = next(cid for cid, e in client.list_characters() if e.slug == choice)

    if not char_id or not entry:
        print(f"No character found for '{choice}'.")
        return

    path = await client.render_character(char_id)
    print(f"Rendered {entry.name} -> {path}")


async def main() -> None:
    actions = {
        "1": fetch_guides,
        "2": render_all_cards,
        "3": render_single_card,
    }

    while True:
        show_menu()
        choice = input("Choose an option: ").strip()

        if choice == "0":
            print("Goodbye.")
            break

        action = actions.get(choice)
        if not action:
            print("Invalid choice. Please enter 0, 1, 2, or 3.")
            continue

        try:
            await action()
        except Exception as exc:
            print(f"Error: {exc}")


if __name__ == "__main__":
    asyncio.run(main())
