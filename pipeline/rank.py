# Score and sort clusters; return top N cluster_ids.
#
# "Hot" = coverage breadth (many publishers) + source diversity (many regions) + recency/momentum.
# We do NOT rank by: social volume, single-source exclusives, or editorial tone.
#
# Weighted impact (aggregator-style):
#   score = 0.65 * publisher_count + 0.25 * region_count + 0.10 * recency_score
# Coverage dominates. Recency half-life is 36h (gentle decay within the morning window).
# Relevance filter (not niche) and anchor-region filter are applied first.
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from models.cluster import Cluster
from models.normalized import NormalizedItem

# Minimum number of distinct publishers in a cluster to appear in the briefing.
# Per-source dedup is now in place (coverage = distinct publishers, not total articles),
# so 3 distinct publishers from 2+ regions is a meaningful and strict global signal.
MIN_COVERAGE_FOR_BRIEFING = 3

# Minimum number of distinct source regions a cluster must span to qualify.
# 2 regions = must be covered by publishers from at least 2 different parts of the world.
# This prevents national/regional stories (e.g. Indian domestic news covered only by Indian
# and Asian outlets) from crowding out genuinely global stories.
MIN_REGIONS_FOR_BRIEFING = 2

# Weights for weighted impact score (coverage dominant, then diversity, then recency).
WEIGHT_COVERAGE = 0.65
WEIGHT_DIVERSITY = 0.25
WEIGHT_RECENCY = 0.10
# Recency half-life: 36h means a 4h-old story decays to ~0.90, a 12h-old to ~0.75.
# Gentle enough that coverage differences dominate; fresh-but-thin stories can't beat
# well-covered stories on recency alone.
RECENCY_HALFLIFE_HOURS = 36.0

# Regions that must be present in at least one cluster member for the story to qualify.
# Prevents LATAM-only, India-only, or Africa-only clusters from reaching the briefing
# even when they technically span 2 regions via a clustering false-positive.
ANCHOR_REGIONS = frozenset({"western", "european", "middle_eastern"})

# Substrings (lowercase) in cluster title that mark it as niche / low relevance for a global morning briefing.
# Such clusters are ranked after "relevant" ones; we prefer fewer, more relevant stories over filling with these.
NICHE_TITLE_PATTERNS = [
    "obituary",
    " obituary:",
    " – live",
    " live ",
    "live blog",
    "live:",
    " vs. ",
    " vs ",
    " v. ",
    " v ",
    "premier league",
    "goat?",
    "goat? ",
    "qualifying",
    " gp ",
    " gp:",
    " to keep ",
    "hopes alive",
    "beat ",
    "today in houston",
    "what time does",
    "how to watch",
    "corrections and clarifications",
    # Seasonal / calendar / local events
    "cuándo empieza",
    "cuando empieza",
    "cuándo son",
    "cuando son",
    "semana santa",
    "feriados",
    "bank holiday",
    "public holiday",
    "when does autumn",
    "when does spring",
    "when does summer",
    "when does winter",
    # Horoscope / lifestyle
    "horoscope",
    "horóscopo",
    "weather forecast",
    # Media/format labels (should be stripped by normalizer, but catch any that slip through)
    "watch:",
    "listen:",
    "read:",
    "in pictures",
    "in photos",
    # Letters / opinion / meta
    "this week in",
    "letters to the editor",
    "letters:",
    "opinion:",
    "podcast:",
    "newsletter:",
    "quiz:",
    # Listicles / soft content
    "recipe",
    "ranked:",
    "top 10",
    "top 5",
    # LATAM / local financial / social content (safety net for clustering false-positives)
    "jubilados",
    "anses",
    "cobran",
    "dólar",
    "pensiones",
    "feriado",
]


def _relevance_score(members: List[NormalizedItem]) -> int:
    """
    Return 1 if the cluster looks like general/news relevance, 0 if niche (sports result, obituary, live blog, etc.).
    Uses the shortest member title as the canonical headline for the cluster.
    """
    titles = [
        (m.title_en or m.title or "").strip().lower()
        for m in members
        if (m.title_en or m.title or "").strip()
    ]
    if not titles:
        return 0
    canonical = min(titles, key=len)
    for pattern in NICHE_TITLE_PATTERNS:
        if pattern in canonical:
            return 0
    return 1


def weighted_score(
    coverage: int,
    region_count: int,
    latest_utc: datetime,
    now_utc: datetime,
) -> float:
    """
    Single scalar: 0.6 * coverage + 0.25 * regions + 0.15 * recency.
    Recency = 1 / (1 + hours_ago / HALFLIFE) so breaking news scores near 1, older decays.
    """
    hours_ago = max(0.0, (now_utc - latest_utc).total_seconds() / 3600.0)
    recency = 1.0 / (1.0 + hours_ago / RECENCY_HALFLIFE_HOURS)
    return (
        WEIGHT_COVERAGE * coverage
        + WEIGHT_DIVERSITY * region_count
        + WEIGHT_RECENCY * recency
    )


def score_breakdown(
    cluster: Cluster,
    normalized_items: List[NormalizedItem],
    now_utc: datetime,
) -> dict:
    """Return coverage, region_count, latest_utc, recency_score, weighted_score for a cluster (for review)."""
    from config import get_region_and_name_for_source

    def _aware(d: datetime) -> datetime:
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d

    item_by_id = {n.id: n for n in normalized_items}
    members = [item_by_id[mid] for mid in cluster.member_ids if mid in item_by_id]
    if not members:
        return {"coverage": 0, "region_count": 0, "recency_score": 0.0, "weighted_score": 0.0}
    coverage = len(members)
    region_count = len({get_region_and_name_for_source(m.source_id)[0] for m in members})
    latest = max(
        (_aware(m.published_at) for m in members if m.published_at),
        default=now_utc,
    )
    if latest.tzinfo is None:
        latest = latest.replace(tzinfo=timezone.utc)
    hours_ago = max(0.0, (now_utc - latest).total_seconds() / 3600.0)
    recency_score = 1.0 / (1.0 + hours_ago / RECENCY_HALFLIFE_HOURS)
    weighted = weighted_score(coverage, region_count, latest, now_utc)
    return {
        "coverage": coverage,
        "region_count": region_count,
        "latest_utc": latest,
        "recency_score": round(recency_score, 3),
        "weighted_score": round(weighted, 2),
    }


def _weighted_score(
    coverage: int,
    region_count: int,
    latest_utc: datetime,
    now_utc: datetime,
) -> float:
    """Alias for weighted_score (used internally)."""
    return weighted_score(coverage, region_count, latest_utc, now_utc)


def rank(
    clusters: List[Cluster],
    normalized_items: List[NormalizedItem],
    top_n: int = 15,
) -> List[Cluster]:
    """
    Rank by: (1) relevance filter (exclude niche), (2) weighted impact score.
    Score = 0.65 * publisher_count + 0.25 * region_count + 0.10 * recency (0–1, 36h half-life).
    Eligibility: coverage >= MIN_COVERAGE_FOR_BRIEFING, regions >= MIN_REGIONS_FOR_BRIEFING,
    and at least one publisher from an ANCHOR_REGION (western / european / middle_eastern).
    """
    from config import get_region_and_name_for_source

    item_by_id = {n.id: n for n in normalized_items}
    now = datetime.now(timezone.utc)

    def _aware(d: datetime) -> datetime:
        return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d

    def get_members(c: Cluster) -> List[NormalizedItem]:
        return [item_by_id[mid] for mid in c.member_ids if mid in item_by_id]

    def sort_key(c: Cluster) -> tuple:
        members = get_members(c)
        if not members:
            return (0, 0.0)
        relevance = _relevance_score(members)
        coverage = len(members)
        regions = len({get_region_and_name_for_source(m.source_id)[0] for m in members})
        latest = max((_aware(m.published_at) for m in members), default=now)
        score = _weighted_score(coverage, regions, latest, now)
        return (relevance, score)

    def _regions(c: Cluster) -> set:
        return {get_region_and_name_for_source(m.source_id)[0] for m in get_members(c)}

    eligible = [
        c for c in clusters
        if len(get_members(c)) >= MIN_COVERAGE_FOR_BRIEFING
        and len(_regions(c)) >= MIN_REGIONS_FOR_BRIEFING
        # At least one publisher must be from a major global-news hub (anchor region).
        # Cuts out LATAM-only, India-only, Africa-only clusters that pass the region
        # count threshold via clustering noise but are regional stories, not global ones.
        and bool(_regions(c) & ANCHOR_REGIONS)
    ]
    sorted_clusters = sorted(eligible, key=sort_key, reverse=True)
    return sorted_clusters[:top_n]


def rank_diagnostic(
    clusters: List[Cluster],
    normalized_items: List[NormalizedItem],
    top_n: int = 15,
) -> dict:
    """Return counts for debugging: clusters by coverage; eligible; top N coverage and relevance."""
    item_by_id = {n.id: n for n in normalized_items}
    by_coverage: dict[int, int] = {}
    for c in clusters:
        members = [item_by_id[mid] for mid in c.member_ids if mid in item_by_id]
        cov = len(members)
        by_coverage[cov] = by_coverage.get(cov, 0) + 1
    top = rank(clusters, normalized_items, top_n=top_n)
    top_coverages = []
    top_relevant = 0
    for c in top:
        members = [item_by_id[mid] for mid in c.member_ids if mid in item_by_id]
        top_coverages.append(len(members))
        top_relevant += _relevance_score(members)
    eligible_count = sum(by_coverage.get(cov, 0) for cov in by_coverage if cov >= MIN_COVERAGE_FOR_BRIEFING)
    return {
        "clusters_by_coverage": dict(sorted(by_coverage.items())),
        "eligible_multi_source": eligible_count,
        "top15_coverage": top_coverages,
        "multi_source_in_top15": sum(1 for x in top_coverages if x >= MIN_COVERAGE_FOR_BRIEFING),
        "relevant_in_top15": top_relevant,
    }
