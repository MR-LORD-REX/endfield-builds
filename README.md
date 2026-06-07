# Endfield Teams - Character Build Guide Generator

A Python-based tool that fetches and renders comprehensive character build guides for **Arknights Endfield**. This project scrapes build data from [Prydwen](https://prydwen.gg/) and generates visually stunning PNG cards with character information, weapon recommendations, gear suggestions, and team compositions.

## Features

Core Capabilities:
- **Async Data Fetching**: Efficiently fetch character guides from Prydwen wiki
- **Automatic Card Rendering**: Generate beautiful PNG build guide cards automatically
- **Comprehensive Build Data**: Includes weapon recommendations, gear sets, skill priorities, team compositions, and synergies
- **Single/Batch Processing**: Render individual character cards or all characters at once
- **Concurrent Operations**: Parallel fetching and rendering for optimal performance
- **Rich Visuals**: Professional card design with character splash art, ratings, and detailed recommendations

## Project Structure

```
endfield-teams/
├── main.py                          # CLI entry point with interactive menu
├── requirements.txt                 # Python dependencies
├── LICENSE.txt                      # MIT License
├── output/                          # Generated PNG cards (output directory)
└── ef_teams/                        # Main package
    ├── __init__.py
    ├── api.py                       # Prydwen API client
    ├── client.py                    # Guide client for loading/rendering
    ├── render.py                    # PNG card rendering engine
    ├── utils.py                     # Utilities (colors, fonts, drawing functions)
    ├── models/
    │   ├── __init__.py
    │   └── guide.py                 # Pydantic data models for guide structure
    └── assets/
        ├── card_assets/             # Card design assets
        ├── fonts/                   # Font files for rendering
        ├── infographics/            # UI elements (icons, frames, etc.)
        └── metadata/
            ├── characters.json      # Character metadata
            └── character_guides.json # Fetched build guides
```

## Requirements

- **Python 3.10+**
- **Dependencies**:
  - `pillow` - Image manipulation and rendering
  - `aiohttp` - Async HTTP client for Prydwen API
  - `asyncio` - Async runtime
  - `beautifulsoup4` - HTML parsing
  - `pydantic` - Data validation and modeling

## Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/MR-LORD-REX/endfield-builds.git
cd endfield-teams
```

### 2. Create Virtual Environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

## Usage

### Interactive CLI Menu

Run the program with:
```bash
python main.py
```

This opens an interactive menu:

```
=== Endfield Character Guide Tools ===
1. Fetch guides from Prydwen
2. Render all character cards
3. Render a single character card
0. Exit
```

### Option 1: Fetch Guides from Prydwen
Fetches the latest build guides for all characters from Prydwen and saves them to `character_guides.json`.

```
Enter choice: 1
Fetching guide for Fluorite (fluorite)...
Fetching guide for Endministrator (endministrator)...
Fetching guide for Laevatain (laevatain)...
[... fetching all characters ...]
Saved 25 guides to ef_teams/assets/metadata/character_guides.json
```

**Output**: Updated JSON file with all character build data

### Option 2: Render All Character Cards
Generates PNG build guide cards for all characters with fetched guides.

```
Enter choice: 2
Rendering 25 characters...
Rendered 25 character cards to output/
```

**Output Examples** (saved in `output/` directory):
- `fluorite.png` - Fluorite's build guide card
- `endministrator.png` - Endministrator's build guide card
- `laevatain.png` - Laevatain's build guide card
- ... (one for each character)

### Option 3: Render Single Character Card
Render a specific character's build guide card.

```
Enter choice: 3
Available characters:
  1. Fluorite (fluorite)
  2. Endministrator (endministrator)
  3. Laevatain (laevatain)
  [...]
  
Enter number or slug: 1
Rendered Fluorite -> output/fluorite.png
```

**Output**: Single PNG card saved to `output/fluorite.png`

## Output Format - Character Build Cards

Each rendered PNG card is **1080×1940 pixels** and includes:

### Card Sections:

1. **Header & Character Info**
   - Character splash art (400px high)
   - Character name and role
   - Rating (e.g., "T0.5 - Enabler")
   - Analysis (Pros/Cons bullets)

2. **Weapons Section**
   - Ranked weapon recommendations (#1-#5)
   - Rarity indicators
   - Solo/Team effectiveness percentages
   - Weapon icons

3. **Best Gear Section**
   - Armor recommendations
   - Gloves recommendations
   - Kit recommendations
   - Gear set names and icons

4. **Skill Priority**
   - Recommended skill upgrade paths
   - Build path for different playstyles

5. **Team Compositions**
   - Multiple team setups with character icons
   - Team member names below icons

6. **Synergy Section**
   - Synergistic characters
   - Element type indicators
   - Full character icons with names

### Example Card Layout:
```
┌─────────────────────────────────────┐
│        CHARACTER SPLASH ART         │
│                                     │
├─────────────────┬─────────────────┤
│   CHARACTER     │  T0.5 - ENABLER │
│     NAME        │                 │
│                 │ PROS (green)    │
│                 │ CONS (red)      │
├─────────────────────────────────────┤
│ WEAPON (1-5 ranked recommendations) │
├─────────────────────────────────────┤
│ GEAR (Best Gear | Alt Gear #2 #3)   │
├─────────────────────────────────────┤
│ SKILL PRIORITY (Build paths)        │
├─────────────────────────────────────┤
│ TEAM COMP (Multiple teams shown)    │
├─────────────────────────────────────┤
│ SYNERGY (Compatible characters)     │
└─────────────────────────────────────┘
```

## Data Models

All character build data is structured using Pydantic models:

### CharacterWithGuide
```python
{
  "name": "Fluorite",
  "slug": "fluorite",
  "guide": CharacterGuide {
    "char_splash": "url_to_splash_art",
    "rating": Rating { rank: "T0.5", role: "Enabler", mode: "..."},
    "analysis": Analysis {
      "pros": ["...", "..."],
      "cons": ["..."]
    },
    "weapons": [
      WeaponRecommendation {
        "rank": "#1",
        "solo": "100%",
        "team": "100%",
        "options": [...]
      },
      ...
    ],
    "gears": [
      GearRecommendation {
        "rank": "Best Gear",
        "pieces": [
          {"type": "Armor", "name": "...", "set": "..."},
          ...
        ],
        "comments": "..."
      },
      ...
    ],
    "skill_orders": ["Build 1: Basic Attack>Battle Skill>Ultimate>Combo Skill", ...],
    "teams": [Team { "name": "Team #1", "members": [...] }, ...],
    "senergies": [Synergy { "name": "...", "element": "..." }, ...],
    "last_updated": "2026-06-07"
  }
}
```

## API Reference

### GuideClient Class

```python
from ef_teams.client import GuideClient

# Initialize
client = GuideClient(
    guides_path="ef_teams/assets/metadata/character_guides.json",
    output_dir="output"
)

# Get single character
entry = client.get("char_id")
entry_by_slug = client.get_by_slug("fluorite")

# List all characters
characters = client.list_characters()

# Render character
output_path = await client.render_character(char_id)

# Render all
output_paths = await client.render_all()
```

### API Client

```python
from ef_teams.api import fetch_character_guide

# Fetch single guide from Prydwen
guide = await fetch_character_guide("fluorite")
```

## Configuration

### Paths (can be customized)
- **Input Guides**: `ef_teams/assets/metadata/character_guides.json`
- **Character Metadata**: `ef_teams/assets/metadata/characters.json`
- **Output Directory**: `output/`

### Rendering Settings
- **Card Size**: 1080×1940 pixels
- **Render Concurrency**: 8 concurrent renders
- **Image Fetch Concurrency**: 32 parallel image downloads
- **Default Margin**: 24 pixels

## Performance

- **Async Operations**: All API calls and image downloads are non-blocking
- **Batch Processing**: Render multiple cards in parallel
- **Smart Caching**: Image caching during rendering for efficiency
- **Rate Limiting**: Built-in 1-second delays when fetching from Prydwen

## Data Sources

- **Build Guides**: [Prydwen.gg](https://prydwen.gg/) - Community-maintained character guides
- **Character Metadata**: Included in `characters.json`
- **Assets**: Character splashes and game assets fetched from official sources

## License

MIT License - See [LICENSE.txt](LICENSE.txt)

Copyright (c) 2026 Sora

## Contributing

Contributions welcome! Feel free to:
- Report issues
- Suggest improvements
- Submit pull requests
- Add new features

## Support

For issues, questions, or feedback:
- Open an issue on [GitHub](https://github.com/MR-LORD-REX/endfield-builds)
- Check existing documentation

---

**Project**: Endfield Teams Character Guide Generator  
**Repository**: https://github.com/MR-LORD-REX/endfield-builds  
**Game**: [Arknights: Endfield](https://arknights.endfield.com/)  
**Data Source**: [Prydwen](https://prydwen.gg/)
