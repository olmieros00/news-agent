# Format briefing and stories for Telegram messages.
# Pure string functions — no API calls, no bot dependency.
# Uses HTML parse mode (much simpler escaping than MarkdownV2).
from __future__ import annotations

from typing import List

from models.briefing import MorningBriefing, Story


def format_briefing(briefing: MorningBriefing, stories: List[Story]) -> str:
    """
    Format the headline list that the user sees when they type /morning.
    Returns a single HTML message string with numbered headlines.
    """
    if not stories:
        return "No stories available. Try again later."
    lines = [f"📰 <b>Morning Briefing — {_esc(briefing.date)}</b>\n"]
    for i, story in enumerate(stories, 1):
        lines.append(f"<b>{i}.</b> {_esc(story.headline)}")
    lines.append("\n<i>Tap a headline to read the full story.</i>")
    return "\n".join(lines)


def format_story(story: Story) -> str:
    """
    Format the expanded view when the user taps a headline.
    Shows: headline, date, body, bias.
    """
    parts = [
        f"<b>{_esc(story.headline)}</b>",
        "",
        f"📅 {_esc(story.date)}",
        "",
        _esc(story.body),
        "",
        f"🔍 <b>Bias</b>\n{_esc(story.bias)}",
    ]
    return "\n".join(parts)


def _esc(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
