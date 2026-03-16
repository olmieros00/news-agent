# Prompt templates for headline, body, bias generation.
# No LLM calls; only strings/templates. Used by pipeline/generate (optional LLM hook).
from __future__ import annotations

from typing import Dict, Any


def get_prompts() -> Dict[str, Any]:
    """Return prompt templates for story generation. Keys: headline, body, bias."""
    return {
        "headline": (
            "You write a new headline for this news story. "
            "Rules: "
            "1. Do NOT copy or paraphrase any single source title. Synthesise from all inputs. "
            "2. Write in plain English only. If source titles are in another language, ignore their wording and write from the facts. "
            "3. Ignore any format prefixes in source titles: WATCH, LISTEN, VIDEO, READ, LIVE, PHOTOS — strip them and focus on the news event. "
            "4. State only the core fact: who/what, what happened, where if relevant. "
            "5. No adjectives unless strictly factual. No editorial tone, no commentary, no spin. "
            "6. One line, 6–12 words. No quotes around the headline."
        ),
        "body": (
            "Write a concise, objective summary of what happened in 5–10 short lines. "
            "Only strongly corroborated facts. No filler, no moralizing. "
            "If something is unclear or disputed, state it clearly."
        ),
        "bias": (
            "Compare how different regional or source groups frame this event. "
            "Example: 'Some Western outlets frame it as X; some Middle Eastern as Y; "
            "some business outlets focus on Z.' Do not decide who is right; only expose framing differences."
        ),
    }
