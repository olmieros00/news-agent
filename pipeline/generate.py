# Per cluster: headline, date, body, bias. No Telegram formatting.
# Headline and body = LLM if OPENAI_API_KEY set; fallback to heuristics otherwise.
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)

from models.briefing import Story
from models.cluster import Cluster
from models.normalized import NormalizedItem

# Stopwords for headline synthesis (skip trivial words).
_HEADLINE_STOP = frozenset(
    {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those", "it", "its", "it's"}
)


def _aware(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d


def _format_date(d: datetime) -> str:
    return _aware(d).strftime("%Y-%m-%d")


def _tokenize(text: str) -> List[str]:
    """Lowercase, letters/numbers only, drop stopwords and very short tokens. Returns list to preserve order where needed."""
    if not text:
        return []
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return [w for w in words if len(w) > 1 and w not in _HEADLINE_STOP]


def _synthesize_headline(members: List[NormalizedItem]) -> str:
    """
    Pick the single cleanest English title from the cluster as the fallback headline.
    Only considers title_en (translated). Falls back to original titles only if no
    translated titles are available at all (e.g. translation step was skipped entirely).
    Among candidates, prefers titles in the 5–12 word range, then shortest.
    """
    # English-confirmed titles first
    en_titles = [m.title_en.strip() for m in members if (m.title_en or "").strip()]
    titles = en_titles if en_titles else [(m.title or "").strip() for m in members if (m.title or "").strip()]
    if not titles:
        return "No headline"
    if len(titles) == 1:
        return titles[0]

    def _word_count(t: str) -> int:
        return len(t.split())

    in_range = [t for t in titles if 5 <= _word_count(t) <= 12]
    candidates = in_range if in_range else titles
    return min(candidates, key=_word_count)


def _ensure_english(text: str, label: str, max_len: int = 2000) -> str:
    """
    Final safety net: if `text` is detectably non-English, translate it.
    `label` is used in log messages ("headline" or "body").
    For headlines: cheap (short string). For bodies: slightly more expensive but still
    only called once per story (max 10 per run).
    Returns original text if detection/translation is unavailable or already English.
    """
    if not text or text in ("No headline", "No summary available."):
        return text
    try:
        import langdetect
        lang = langdetect.detect(text[:500])
        if lang == "en":
            return text
        try:
            from deep_translator import GoogleTranslator
            translated = GoogleTranslator(source="auto", target="en").translate(text[:max_len])
            if translated and translated.strip():
                log.info("%s translated from %s to English (%d chars)", label, lang, len(text))
                return translated.strip()
        except Exception as e:
            log.warning("%s translation failed (%s): %s", label, lang, e)
    except Exception:
        pass
    return text


def _ensure_english_headline(headline: str) -> str:
    return _ensure_english(headline, "Headline", max_len=300)


def _ensure_english_body(body: str) -> str:
    return _ensure_english(body, "Body", max_len=1500)


def _llm_client(api_key: str):
    """Return an OpenAI client or None if openai is not installed."""
    try:
        import openai
        return openai.OpenAI(api_key=api_key)
    except ImportError:
        log.warning("openai package not installed; LLM generation disabled. pip install openai")
        return None


def _generate_headline_llm(
    titles: List[str],
    snippets: List[str],
    prompt_instruction: str,
    api_key: str,
) -> Optional[str]:
    """Call OpenAI to produce one neutral headline. Returns None on failure or missing key."""
    if not api_key or not titles:
        return None
    client = _llm_client(api_key)
    if client is None:
        return None
    try:
        combined = "Titles from different sources:\n" + "\n".join(f"- {t}" for t in titles[:10])
        if snippets:
            combined += "\n\nShort snippets:\n" + "\n".join(s[:200] for s in snippets[:5] if s)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_instruction},
                {"role": "user", "content": combined + "\n\nSynthesize one new headline from the above. One line, no quotes. Reasoned, fair, unbiased, straight to the point."},
            ],
            max_tokens=80,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text[:200]
    except Exception as e:
        log.warning("LLM headline generation failed: %s", e)
    return None


def _generate_body_llm(
    snippets: List[str],
    prompt_instruction: str,
    api_key: str,
) -> Optional[str]:
    """Call OpenAI to produce a concise, objective body from merged snippets. Returns None on failure."""
    if not api_key or not snippets:
        return None
    client = _llm_client(api_key)
    if client is None:
        return None
    try:
        combined = "Snippets from different sources:\n" + "\n\n".join(
            f"[{i+1}] {s[:600]}" for i, s in enumerate(snippets[:10]) if s
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_instruction},
                {"role": "user", "content": combined + "\n\nWrite a concise, objective body (5–10 short lines). Only corroborated facts. No filler, no moralizing."},
            ],
            max_tokens=600,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception as e:
        log.warning("LLM body generation failed: %s", e)
    return None


def _generate_bias_llm(
    region_snippets: Dict[str, List[str]],
    prompt_instruction: str,
    api_key: str,
) -> Optional[str]:
    """Call OpenAI to compare framing across regional source groups. Returns None on failure."""
    if not api_key or not region_snippets:
        return None
    client = _llm_client(api_key)
    if client is None:
        return None
    try:
        parts = []
        for region, snips in region_snippets.items():
            combined_snip = " ".join(s[:200] for s in snips[:3] if s)
            if combined_snip:
                parts.append(f"[{region}]: {combined_snip}")
        if not parts:
            return None
        combined = "\n\n".join(parts)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_instruction},
                {"role": "user", "content": combined + "\n\nBriefly compare how each regional group frames this event. 2–4 lines. No judgment."},
            ],
            max_tokens=200,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return text
    except Exception as e:
        log.warning("LLM bias generation failed: %s", e)
    return None


def generate_stories(
    ranked_clusters: List[Cluster],
    normalized_items: List[NormalizedItem],
    source_registry: List[Dict[str, Any]],
) -> List[Story]:
    """
    For each cluster, produce one Story: headline (neutral), date, body, bias.
    Headline: generated by LLM (if OPENAI_API_KEY set) or synthesized from consensus words across sources. We do not pick one outlet's title.
    """
    from config import get_region_and_name_for_source, get_settings, get_prompts
    item_by_id = {n.id: n for n in normalized_items}
    settings = get_settings()
    prompts = get_prompts()
    headline_prompt = (prompts.get("headline") or "").strip()
    body_prompt = (prompts.get("body") or "").strip()
    bias_prompt = (prompts.get("bias") or "").strip()
    use_llm = bool(settings.openai_api_key)
    if use_llm:
        log.info("LLM generation enabled (gpt-4o-mini). Generating headline/body/bias for %d clusters.", len(ranked_clusters))
    else:
        log.info("LLM generation disabled (no OPENAI_API_KEY). Using heuristic fallbacks.")
    stories: List[Story] = []

    region_labels = {
        "western": "Western", "european": "European", "middle_eastern": "Middle Eastern",
        "asia": "Asia", "business": "Business", "africa": "Africa",
        "latin_america": "Latin America", "other": "Other",
    }

    for cluster in ranked_clusters:
        members = [item_by_id[mid] for mid in cluster.member_ids if mid in item_by_id]
        if not members:
            continue

        # Only use English-confirmed titles for LLM and fallback.
        # title_en is set by the translate step; if it's None the translation failed,
        # and passing the original non-English title would contaminate the output.
        all_titles = [m.title_en.strip() for m in members if (m.title_en or "").strip()]
        # Fallback: if no translated titles at all (e.g. translation step skipped), use original
        if not all_titles:
            all_titles = [(m.title or "").strip() for m in members if (m.title or "").strip()]
        all_snippets = [(m.body_en or m.body_or_snippet or "").strip() for m in members if (m.body_en or m.body_or_snippet or "").strip()]

        # Headline: LLM or consensus-word synthesis
        headline = None
        if use_llm and headline_prompt:
            headline = _generate_headline_llm(all_titles, all_snippets, headline_prompt, settings.openai_api_key)
        if not headline:
            headline = _synthesize_headline(members)

        # Final language guard: if the headline is not English, attempt a quick translation.
        # This catches leakage from failed translations or LLM hallucinations.
        headline = _ensure_english_headline(headline)

        # Date: latest published in cluster
        latest = max(_aware(m.published_at) for m in members)
        date_str = _format_date(latest)

        # Body: LLM summary or merged snippets (fallback)
        body = None
        if use_llm and body_prompt:
            body = _generate_body_llm(all_snippets, body_prompt, settings.openai_api_key)
        if not body:
            body = " ".join(all_snippets)[:1200].strip() or "No summary available."

        # Final language guard on body — same as headline guard
        body = _ensure_english_body(body)

        # Bias: group snippets by region, ask LLM to compare framing; fallback = coverage list
        by_region_names: Dict[str, List[str]] = {}
        by_region_snippets: Dict[str, List[str]] = {}
        for m in members:
            region, name = get_region_and_name_for_source(m.source_id)
            label = region_labels.get(region, region)
            by_region_names.setdefault(label, [])
            by_region_snippets.setdefault(label, [])
            if name not in by_region_names[label]:
                by_region_names[label].append(name)
            snip = (m.body_en or m.body_or_snippet or "").strip()
            if snip:
                by_region_snippets[label].append(snip)

        bias = None
        if use_llm and bias_prompt and len(by_region_snippets) >= 2:
            bias = _generate_bias_llm(by_region_snippets, bias_prompt, settings.openai_api_key)
        if not bias:
            coverage_parts = [f"{r}: {', '.join(sorted(names))}" for r, names in sorted(by_region_names.items())]
            bias = "Covered by " + "; ".join(coverage_parts) + "."

        stories.append(
            Story(
                story_id=cluster.cluster_id,
                cluster_id=cluster.cluster_id,
                headline=headline,
                date=date_str,
                body=body,
                bias=bias,
            )
        )
    return stories
