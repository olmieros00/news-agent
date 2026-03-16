# Generated story (headline, date, body, bias) and morning briefing (ordered story ids).
from dataclasses import dataclass


@dataclass
class Story:
    story_id: str
    cluster_id: str
    headline: str
    date: str
    body: str
    bias: str


@dataclass
class MorningBriefing:
    briefing_id: str
    date: str  # morning date
    story_ids: list[str]
