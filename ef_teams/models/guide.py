from pydantic import BaseModel, ConfigDict, Field


class WeaponOption(BaseModel):
    name: str = ""
    potential: str = ""
    icon_url: str = ""
    rarity: int | None = None


class WeaponRecommendation(BaseModel):
    rank: str
    solo: str | None = None
    team: str | None = None
    options: list[WeaponOption] = Field(default_factory=list)


class GearOption(BaseModel):
    name: str = ""
    icon_url: str = ""
    rarity: int | None = None


class GearPiece(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    type: str
    icon_url: str | None = None
    name: str | None = None
    gear_set: str | None = Field(default=None, alias="set")


class GearRecommendation(BaseModel):
    rank: str
    solo: str | None = None
    team: str | None = None
    options: list[GearOption] = Field(default_factory=list)
    comments: str | None = None
    pieces: list[GearPiece] = Field(default_factory=list)


class TeamMember(BaseModel):
    icon_url: str | None = None
    name: str | None = None


class Team(BaseModel):
    name: str | None = None
    members: list[TeamMember] = Field(default_factory=list)


class Synergy(BaseModel):
    icon_url: str | None = None
    element_icon: str | None = None
    name: str | None = None
    element: str | None = None

class Rating(BaseModel):
    rank: str | None = None
    role: str | None = None
    mode: str | None = None

class Analysis(BaseModel):
    pros: list[str] = Field(default_factory=list)
    cons: list[str] = Field(default_factory=list)

class CharacterGuide(BaseModel):
    char_splash: str
    weapons: list[WeaponRecommendation] = Field(default_factory=list)
    gears: list[GearRecommendation] = Field(default_factory=list)
    skill_orders: list[str] = Field(default_factory=list)
    teams: list[Team] = Field(default_factory=list)
    senergies: list[Synergy] = Field(default_factory=list)
    last_updated: str
    rating: Rating | None = None
    analysis: Analysis | None = None

class CharacterSummary(BaseModel):
    name: str
    slug: str
    icon_url: str




class CharacterWithGuide(BaseModel):
    name: str
    slug: str
    guide: CharacterGuide | None = None
