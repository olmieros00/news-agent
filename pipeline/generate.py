# Per cluster: classify as business signal or noise, extract structured data.
# Single LLM call per cluster handles relevance, company, vertical, signal_type, headline, body.
from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

from models.briefing import Story
from models.cluster import Cluster
from models.normalized import NormalizedItem


def _aware(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d


def _format_date(d: datetime) -> str:
    return _aware(d).strftime("%Y-%m-%d")


def _claude_call(system: str, user: str, max_tokens: int, api_key: str) -> Optional[str]:
    """Call Anthropic Claude. Returns response text or None on failure."""
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        text = (response.content[0].text or "").strip()
        return text if text else None
    except ImportError:
        log.warning("anthropic package not installed; pip install anthropic")
        return None
    except Exception as e:
        log.warning("Claude API call failed: %s", e)
        return None


def _classify_and_extract(
    titles: List[str],
    snippets: List[str],
    source_names: List[str],
    prompt_instruction: str,
    api_key: str,
) -> Optional[dict]:
    """Single Claude call: classify relevance + extract company/vertical/signal/headline/body.
    Returns parsed dict or None on failure."""
    if not api_key or not titles:
        return None
    combined = "Titles:\n" + "\n".join(f"- {t}" for t in titles[:10])
    if snippets:
        combined += "\n\nSnippets:\n" + "\n".join(
            f"[{i+1}] {s[:600]}" for i, s in enumerate(snippets[:10]) if s
        )
    if source_names:
        combined += "\n\nSources: " + ", ".join(source_names[:10])

    raw = _claude_call(prompt_instruction, combined, max_tokens=500, api_key=api_key)
    if not raw:
        return None
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        log.warning("LLM returned invalid JSON: %s", raw[:200])
        return None


def _fallback_headline(members: List[NormalizedItem]) -> str:
    """Pick the shortest clean title from the cluster as fallback."""
    titles = [
        (m.title_en or m.title or "").strip()
        for m in members if (m.title_en or m.title or "").strip()
    ]
    if not titles:
        return "No headline"
    return min(titles, key=len)


def generate_stories(
    ranked_clusters: List[Cluster],
    normalized_items: List[NormalizedItem],
    source_registry: List[Dict[str, Any]],
) -> List[Story]:
    """For each cluster, classify as business signal or noise via Claude.
    Returns only relevant business stories with company, vertical, signal_type."""
    from config import get_region_and_name_for_source, get_settings, get_prompts

    item_by_id = {n.id: n for n in normalized_items}
    settings = get_settings()
    prompts = get_prompts()
    classify_prompt = (prompts.get("classify_and_extract") or "").strip()

    llm_key = settings.anthropic_api_key or settings.openai_api_key
    use_llm = bool(llm_key and classify_prompt)

    if use_llm:
        log.info("Business signal extraction enabled (Claude). Processing %d clusters.", len(ranked_clusters))
    else:
        log.info("No LLM key set. Returning all clusters without filtering.")

    stories: List[Story] = []
    skipped = 0

    for cluster in ranked_clusters:
        members = [item_by_id[mid] for mid in cluster.member_ids if mid in item_by_id]
        if not members:
            continue

        all_titles = [
            (m.title_en or m.title or "").strip()
            for m in members if (m.title_en or m.title or "").strip()
        ]
        all_snippets = [
            (m.body_en or m.body_or_snippet or "").strip()
            for m in members if (m.body_en or m.body_or_snippet or "").strip()
        ]
        source_names = []
        for m in members:
            _, name = get_region_and_name_for_source(m.source_id)
            if name not in source_names:
                source_names.append(name)

        latest = max(_aware(m.published_at) for m in members)
        date_str = _format_date(latest)

        if use_llm:
            result = _classify_and_extract(
                all_titles, all_snippets, source_names, classify_prompt, llm_key,
            )
            if result and not result.get("relevant", False):
                skipped += 1
                continue

            if result and result.get("relevant"):
                stories.append(Story(
                    story_id=cluster.cluster_id,
                    cluster_id=cluster.cluster_id,
                    headline=result.get("headline") or _fallback_headline(members),
                    date=date_str,
                    body=result.get("body") or " ".join(all_snippets)[:800] or "No summary available.",
                    company=result.get("company") or "",
                    vertical=result.get("vertical") or "",
                    signal_type=result.get("signal_type") or "",
                    source=", ".join(source_names),
                    priority=result.get("priority") or "standard",
                ))
                continue

        # Fallback (no LLM or LLM failed): include everything, no classification
        stories.append(Story(
            story_id=cluster.cluster_id,
            cluster_id=cluster.cluster_id,
            headline=_fallback_headline(members),
            date=date_str,
            body=" ".join(all_snippets)[:800] or "No summary available.",
            company="",
            vertical="",
            signal_type="",
            source=", ".join(source_names),
            priority="standard",
        ))

    if skipped:
        log.info("Filtered out %d non-business clusters.", skipped)

    # Sort: high-priority (B2C/retail/D2C) first, then standard
    stories.sort(key=lambda s: (0 if s.priority == "high" else 1))

    high = sum(1 for s in stories if s.priority == "high")
    log.info("Returning %d business signals (%d high-priority B2C, %d standard).", len(stories), high, len(stories) - high)
    return stories
