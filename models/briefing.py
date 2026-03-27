# Generated story (business intent signal) and morning briefing (ordered story ids).
from dataclasses import dataclass, field


@dataclass
class Story:
    story_id: str
    cluster_id: str
    headline: str
    date: str
    body: str
    company: str = ""
    vertical: str = ""
    signal_type: str = ""
    source: str = ""
    priority: str = ""  # "high" = B2C/retail/D2C, "standard" = other verticals


@dataclass
class MorningBriefing:
    briefing_id: str
    date: str
    story_ids: list[str] = field(default_factory=list)
