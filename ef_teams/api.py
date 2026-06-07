from pathlib import Path

from aiohttp import ClientSession
from curl_cffi.requests import AsyncSession
from bs4 import BeautifulSoup
import json
import asyncio
import re
from datetime import datetime , timedelta , timezone

from .models import (
    CharacterGuide,
    CharacterSummary,
    GearOption,
    GearPiece,
    GearRecommendation,
    Synergy,
    Team,
    TeamMember,
    WeaponOption,
    WeaponRecommendation,
    Rating,
    Analysis
)

asset_path=Path(__file__).parent / "assets"
card_assets_path=asset_path / "card_assets"
infographic_path=asset_path / "infographics"
metadata_path=asset_path / "metadata"



characters_url="https://endfieldtools.dev/localdb/optimized/characters/characters-list.json"

guide_base_url="https://www.prydwen.gg/arknights-endfield/characters/{character_slug}"

side_icon="https://endfieldtools.dev/assets/images/endfield/charhorheadicon/{character_slug}.png"

full_icon="https://cdn.prydwen.gg/images/arknights-endfield/characters/{character_slug}_full.webp"

# char_data="https://endfieldtools.dev/localdb/optimized/characters/details/{character_slug}.json"

# type_icon="https://endfieldtools.dev/assets/images/icons/{type_slug}.webp"

# profession_icon="https://endfieldtools.dev/assets/images/endfield/charprofessionicon/icon_profession_{profession_slug}.png"



async def fetch_characters() -> dict[str, CharacterSummary] | None:
    try:
        async with ClientSession() as session:
            async with session.get(characters_url) as response:
                if response.status == 200:
                    all_characters: dict[str, CharacterSummary] = {}
                    data=await response.json()
                    for k,v in data.items():
                        character_id=k
                        character_name=v.get("engName","Unknown")
                        slug=v.get("slug","unknown")
                        icon_url=side_icon.format(character_slug=slug)
                        all_characters[character_id]=CharacterSummary(
                            name=character_name,
                            slug=slug,
                            icon_url=icon_url,
                        )
                    with open(metadata_path / "characters.json","w",encoding="utf-8") as f:
                        json.dump(
                            {k: v.model_dump() for k, v in all_characters.items()},
                            f,
                            ensure_ascii=False,
                            indent=4,
                        )
                    return all_characters
                else:
                    print(f"Failed to fetch characters: {response.status}")
                    return None
    except Exception as e:
        print(f"An error occurred while fetching characters: {e}")
        return None

def get_last_updated(soup: BeautifulSoup) -> str:
    last_updated=soup.find("div",class_="last-update")
    if last_updated:
        info=last_updated.find("div",class_="info")
        if info:
            return info.get_text(strip=True)
        else:
            now=datetime.now(timezone.utc).strftime("%Y-%m-%d")
            return now
    now=datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return now
    
def parse_weapon_section(section: BeautifulSoup) -> list[WeaponRecommendation]:
    weapon_section=section
    weapons: list[WeaponRecommendation] = []
    if weapon_section:
        rows=weapon_section.find_all("div",class_="single-row")
        for row in rows:
            if row.find_parent("div", class_=re.compile(r"specialist|special", re.IGNORECASE)):
                continue
            preceding_h6 = row.find_previous("h6")
            if preceding_h6 and "specialist" in preceding_h6.get_text(strip=True).lower():
                continue

            rank = ""
            rank_tag=row.find("div",class_="number")
            if rank_tag:
                rank=rank_tag.text.strip()

            solo = None
            solo_tag=row.find("div",class_="number rating")
            if solo_tag:
                span=solo_tag.find("span")
                if span:
                    solo=span.text.strip()

            team = None
            team_tag=row.find("div",class_="number rating alt")
            if team_tag:
                span=team_tag.find("span")
                if span:
                    team=span.text.strip()

            options: list[WeaponOption] = []
            set_tag = row.find("div", class_="sets")
            if set_tag:
                accordion_items = set_tag.find_all(
                    "div", class_=re.compile(r"\bpw-accordion-item\b")
                )
                for item in accordion_items:
                    btn = item.find("button")
                    if not btn:
                        continue
                    name_span = btn.find("span", class_=lambda c: c is not None and "name" in c)
                    cone_span = btn.find("span", class_="cone-super")
                    img       = btn.find("img", alt="Weapon")

                    rarity = None
                    if name_span:
                        classes = name_span.get("class") or []
                        if classes:
                            rarity_match = re.search(r"rarity-(\d+)", " ".join(classes))
                            if rarity_match:
                                rarity = int(rarity_match.group(1))

                    options.append(WeaponOption(
                        name=name_span.get_text(strip=True) if name_span else "",
                        potential=cone_span.get_text(strip=True) if cone_span else "",
                        icon_url=img["src"] if img else "",
                        rarity=rarity,
                    ))

            weapons.append(WeaponRecommendation(
                rank=rank,
                solo=solo,
                team=team,
                options=options,
            ))
    return weapons
    
def parse_gear_section(section: BeautifulSoup) -> list[GearRecommendation]:
    gear_section=section
    gears: list[GearRecommendation] = []
    if gear_section:
        rows=gear_section.find_all("div",class_="single-row")
        all_comments=gear_section.find_all("div",class_="comments gear")
        for i,row in enumerate(rows):
            rank = ""
            rank_tag=row.find("div",class_="number")
            if rank_tag:
                rank=rank_tag.text.strip()

            solo = None
            solo_tag=row.find("div",class_="number rating")
            if solo_tag:
                span=solo_tag.find("span")
                if span:
                    solo=span.text.strip()

            team = None
            team_tag=row.find("div",class_="number rating alt")
            if team_tag:
                span=team_tag.find("span")
                if span:
                    team=span.text.strip()

            options: list[GearOption] = []
            set_tag = row.find("div", class_="sets")
            if set_tag:
                accordion_items = set_tag.find_all(
                    "div", class_=re.compile(r"\bpw-accordion-item\b")
                )
                for item in accordion_items:
                    btn = item.find("button")
                    if not btn:
                        continue
                    name_span = btn.find("span", class_=lambda c: c is not None and "name" in c)
                    img_icon=btn.find("img", alt="Gear Set")

                    rarity = None
                    if name_span:
                        classes = name_span.get("class") or []
                        if classes:
                            rarity_match = re.search(r"rarity-(\d+)", " ".join(classes))
                            if rarity_match:
                                rarity = int(rarity_match.group(1))

                    options.append(GearOption(
                        name=name_span.get_text(strip=True) if name_span else "",
                        icon_url=img_icon["src"] if img_icon else "",
                        rarity=rarity,
                    ))

            comments = None
            pieces: list[GearPiece] = []
            comments_tag=all_comments[i] if i < len(all_comments) else None
            if comments_tag:
                para=comments_tag.find("p")
                if para:
                    comments=para.get_text(strip=True)
                gear_pieces=comments_tag.find("div",class_="gear-pieces")
                if gear_pieces:
                    for piece in gear_pieces.find_all("div",class_="column"):
                        piece_type = ""
                        type_p=piece.find("p",class_="gear-type")
                        if type_p:
                            piece_type=type_p.get_text(strip=True)

                        icon_url = None
                        piece_name = None
                        gear_set = None
                        main_sec=piece.find("div",class_="endfield-gear-icon")
                        if main_sec:
                            img=main_sec.find("strong",class_="endfield-image")
                            if img and img.find("img"):
                                icon_url=img.find("img")["src"]
                            name_tag=main_sec.find("strong",class_="weapon-name")
                            if name_tag:
                                piece_name=name_tag.get_text(strip=True)
                            suite_name=main_sec.find("span")
                            if suite_name:
                                gear_set=suite_name.get_text(strip=True)

                        pieces.append(GearPiece(
                            type=piece_type,
                            icon_url=icon_url,
                            name=piece_name,
                            gear_set=gear_set,
                        ))

            gears.append(GearRecommendation(
                rank=rank,
                solo=solo,
                team=team,
                options=options,
                comments=comments,
                pieces=pieces,
            ))
    return gears
                            
def parse_skill_order(section:BeautifulSoup):
    all_sections=section.find_all("blockquote",class_="skill-order")
    skill_orders=[]
    for sec in all_sections:
        p=sec.find("p")
        if p:
            text=p.get_text(strip=True)
            skill_orders.append(text)
    return skill_orders

def parse_team_section(section: BeautifulSoup) -> list[Team]:
    team_section=section
    teams: list[Team] = []
    if team_section:
        team_rows=team_section.find_all("div",class_="single-team")
        for team in team_rows:
            team_name = None
            name_tag=team.find("div",class_="team-name")
            if name_tag:
                team_name=name_tag.get_text(strip=True)

            members: list[TeamMember] = []
            team_members=team.find("div",class_="team-setup")
            if team_members:
                team_member_spans=team_members.find_all("span", recursive=False)
                for member in team_member_spans:
                    avatar=member.find("div",class_="avatar")
                    if avatar:
                        icon_url = None
                        img=avatar.find("img")
                        if img:
                            icon_url=img["src"]
                        member_name = None
                        name_span=member.find("span",class_="emp-name")
                        if name_span:
                            member_name=name_span.get_text(strip=True)
                        members.append(TeamMember(
                            icon_url=icon_url,
                            name=member_name,
                        ))

            teams.append(Team(name=team_name, members=members))
    return teams

def parse_senergy_section(section: BeautifulSoup) -> list[Synergy]:
    senergy_section=section
    senergies: list[Synergy] = []
    if senergy_section:
        col=senergy_section.find_all("div",class_="column")
        for c in col:
            icon_url = None
            element_icon = None
            avatar=c.find("div",class_="avatar")
            if avatar:
                img=avatar.find("img")
                if img:
                    icon_url=img["src"]
                element_span=avatar.find("span",class_="floating-element")
                if element_span:
                    element_img=element_span.find("img")
                    if element_img:
                        element_icon=element_img["src"]

            name = None
            name_tag=c.find("span",class_="emp-name")
            if name_tag:
                name=name_tag.get_text(strip=True)

            element = None
            element_tag=c.find("span",class_="element-display")
            if element_tag:
                element=element_tag.get_text(strip=True)

            senergies.append(Synergy(
                icon_url=icon_url,
                element_icon=element_icon,
                name=name,
                element=element,
            ))
    return senergies


def parse_rating(section: BeautifulSoup) -> Rating:
    rating_section=section.find("div",class_="ratings")
    rating: Rating = Rating()
    if rating_section:
        role_tag=rating_section.find("h6",class_="ake-small-role")
        if role_tag:
            role=role_tag.get_text(strip=True)
            rating.role=role
        rating_tag=rating_section.find("div",class_="rating-box-container")
        if rating_tag:
            rating_box=rating_tag.find("div",class_="rating-box")
            if rating_box:
                rank=rating_box.get_text(strip=True)
                rating.rank=rank
            p=rating_tag.find("p")
            if p:
                rating_name=p.get_text(strip=True)
                rating.mode=rating_name
    return rating

def parse_analysis(soup:BeautifulSoup) -> Analysis:
    section=soup.find("div",class_="section-analysis")
    pros=[]
    cons=[]
    if section:
        pros_sec=section.find("div",class_="box pros")
        if pros_sec:
            all_items=pros_sec.find_all("li")
            for item in all_items:
                pros.append(item.get_text(strip=True))
        cons_sec=section.find("div",class_="box cons")
        if cons_sec:
            all_items=cons_sec.find_all("li")
            for item in all_items:
                cons.append(item.get_text(strip=True))
    return Analysis(pros=pros, cons=cons)

async def fetch_character_guide(slug: str) -> CharacterGuide | None:
    url = guide_base_url.format(character_slug=slug)
    try:
        async with AsyncSession() as session:
            response = await session.get(
                url,
                impersonate="chrome124",   
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                all=soup.find_all("div", class_="build-setup weapons")
                team_section=soup.find("div",class_="special-team-viewer")
                senergy_section=soup.find("div",class_="team-calc-overview synergy-info")
                if not all:
                    print(f"No weapon section found for {slug}")
                    return None

                weapon_section = all[0]
                gear_section = None
                for section in all[1:]:
                    if section.find("div", class_="comments gear"):
                        gear_section = section
                        break
                if not gear_section and len(all) > 1:
                    gear_section = all[1]
                weapons, gears, skill_orders, teams, senergies , now , rating , analysis  = await asyncio.gather(
                    asyncio.to_thread(parse_weapon_section, weapon_section),
                    asyncio.to_thread(parse_gear_section, gear_section) if gear_section else asyncio.to_thread(list),
                    asyncio.to_thread(parse_skill_order, soup),
                    asyncio.to_thread(parse_team_section, team_section) if team_section else asyncio.to_thread(list),
                    asyncio.to_thread(parse_senergy_section, senergy_section) if senergy_section else asyncio.to_thread(list),
                    asyncio.to_thread(get_last_updated, soup),
                    asyncio.to_thread(parse_rating, soup),
                    asyncio.to_thread(parse_analysis, soup),
                )
                full_icon_url=full_icon.format(character_slug=slug)
                return CharacterGuide(
                    char_splash=full_icon_url,
                    weapons=weapons,
                    gears=gears,
                    skill_orders=skill_orders,
                    teams=teams,
                    senergies=senergies,
                    last_updated=now,
                    rating=rating,
                    analysis=analysis,
                )
            else:
                print(f"Failed {slug}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching {slug}: {e}")
    return None
                    
    
