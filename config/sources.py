# Source registry: source_id, type, endpoint, tier, role, region, auth, status.
# No fetching; only structure.
# Status: usable | needs_key | restricted | unconfirmed
# Use get_usable_connector_sources() for the first connector set (usable + needs_key only).

from typing import TypedDict


class SourceConfig(TypedDict, total=False):
    source_id: str
    name: str
    domain: str
    tier: int
    role: str
    source_type: str  # api | rss | rss_pattern
    endpoint_url: str
    status: str  # usable | needs_key | restricted | unconfirmed
    auth_required: bool
    auth_key_env: str
    region: str
    notes: str


# Italian business news sources.
SOURCE_REGISTRY: list[SourceConfig] = [
    # ---- Business & economy ----
    {
        "source_id": "sole24ore_economia",
        "name": "Il Sole 24 Ore – Economia",
        "domain": "ilsole24ore.com",
        "tier": 1,
        "role": "Business & economy",
        "source_type": "rss",
        "endpoint_url": "https://www.ilsole24ore.com/rss/economia.xml",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "sole24ore_finanza",
        "name": "Il Sole 24 Ore – Finanza",
        "domain": "ilsole24ore.com",
        "tier": 1,
        "role": "Business & economy",
        "source_type": "rss",
        "endpoint_url": "https://www.ilsole24ore.com/rss/finanza.xml",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "sole24ore_startup",
        "name": "Il Sole 24 Ore – Startups",
        "domain": "ilsole24ore.com",
        "tier": 1,
        "role": "Business & economy",
        "source_type": "rss",
        "endpoint_url": "https://www.ilsole24ore.com/rss/finanza-e-mercati/startups.xml",
        "status": "disabled",
        "auth_required": False,
        "region": "italy",
        "notes": "404 — URL may have changed",
    },
    {
        "source_id": "corriere_economia",
        "name": "Corriere della Sera – Economia",
        "domain": "corriere.it",
        "tier": 1,
        "role": "Business & economy",
        "source_type": "rss",
        "endpoint_url": "https://www.corriere.it/rss/economia.xml",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "ansa_economia",
        "name": "ANSA – Economia",
        "domain": "ansa.it",
        "tier": 1,
        "role": "Business & economy",
        "source_type": "rss",
        "endpoint_url": "https://www.ansa.it/sito/notizie/economia/economia_rss.xml",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "italiaoggi",
        "name": "Italia Oggi",
        "domain": "italiaoggi.it",
        "tier": 1,
        "role": "Business & economy",
        "source_type": "rss",
        "endpoint_url": "https://www.italiaoggi.it/rss/economia-e-politica.xml",
        "status": "disabled",
        "auth_required": False,
        "region": "italy",
        "notes": "404 — URL may have changed",
    },
    # ---- Startups & venture capital ----
    {
        "source_id": "bebeez",
        "name": "BeBeez",
        "domain": "bebeez.it",
        "tier": 1,
        "role": "Startups & VC",
        "source_type": "rss",
        "endpoint_url": "https://bebeez.it/feed",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "startupitalia",
        "name": "StartupItalia",
        "domain": "startupitalia.eu",
        "tier": 1,
        "role": "Startups & VC",
        "source_type": "rss",
        "endpoint_url": "https://startupitalia.eu/feed",
        "status": "disabled",
        "auth_required": False,
        "region": "italy",
        "notes": "403 — blocked",
    },
    {
        "source_id": "scaleupitaly",
        "name": "ScaleUp Italy",
        "domain": "scaleupitaly.com",
        "tier": 1,
        "role": "Startups & VC",
        "source_type": "rss",
        "endpoint_url": "https://scaleupitaly.com/feed",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "wired_italia",
        "name": "Wired Italia",
        "domain": "wired.it",
        "tier": 1,
        "role": "Startups & VC",
        "source_type": "rss",
        "endpoint_url": "https://www.wired.it/feed/rss",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    # ---- Discovery — regional ----
    {
        "source_id": "milanotoday_economia",
        "name": "MilanoToday",
        "domain": "milanotoday.it",
        "tier": 2,
        "role": "Discovery — regional",
        "source_type": "rss",
        "endpoint_url": "https://www.milanotoday.it/rss",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    # ---- Ecommerce — Tier 1 ----
    {
        "source_id": "netcomm",
        "name": "Netcomm",
        "domain": "consorzionetcomm.it",
        "tier": 1,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.consorzionetcomm.it/categoria/news/feed/",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "ecommerce_italia_casaleggio",
        "name": "Ecommerce Italia (Casaleggio)",
        "domain": "ecommerceitalia.info",
        "tier": 1,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.ecommerceitalia.info/category/news/feed/",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "corcom",
        "name": "CorCom",
        "domain": "corrierecomunicazioni.it",
        "tier": 1,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.corrierecomunicazioni.it/feed/",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "digital4",
        "name": "Digital4",
        "domain": "digital4.biz",
        "tier": 1,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.digital4.biz/feed/",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "ninja_marketing",
        "name": "Ninja Marketing",
        "domain": "ninjamarketing.it",
        "tier": 1,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.ninjamarketing.it/feed/",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "pagamenti_digitali",
        "name": "Pagamenti Digitali",
        "domain": "pagamentidigitali.it",
        "tier": 1,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.pagamentidigitali.it/feed/",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
    {
        "source_id": "qapla_blog",
        "name": "Qapla' Blog",
        "domain": "qapla.it",
        "tier": 1,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.qapla.it/blog/feed/",
        "status": "disabled",
        "auth_required": False,
        "region": "italy",
        "notes": "403 — blocked",
    },
    # ---- Ecommerce — Tier 2 ----
    {
        "source_id": "osservatori_polimi",
        "name": "Osservatori PoliMi",
        "domain": "osservatori.net",
        "tier": 2,
        "role": "Ecommerce",
        "source_type": "rss",
        "endpoint_url": "https://www.osservatori.net/feed/",
        "status": "usable",
        "auth_required": False,
        "region": "italy",
    },
]


def get_source_registry() -> list[SourceConfig]:
    """Return the full source registry (all statuses)."""
    return SOURCE_REGISTRY


def get_usable_connector_sources() -> list[SourceConfig]:
    """Return only sources that should have production connectors built: status usable or needs_key."""
    return [s for s in SOURCE_REGISTRY if s["status"] in ("usable", "needs_key")]


def get_sources_by_status(status: str) -> list[SourceConfig]:
    """Return sources with the given status."""
    return [s for s in SOURCE_REGISTRY if s["status"] == status]


def get_region_and_name_for_source(source_id: str) -> tuple[str, str]:
    """Return (region, display_name) for source_id. Default ('other', source_id)."""
    for s in SOURCE_REGISTRY:
        if s.get("source_id") == source_id:
            return (s.get("region") or "other", s.get("name") or source_id)
    return ("other", source_id)
