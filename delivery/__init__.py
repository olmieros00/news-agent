# Telegram delivery layer. No ingestion, no pipeline.
# Imports are lazy to avoid requiring python-telegram-bot when only using the pipeline.

__all__ = ["run_bot", "format_briefing", "format_story"]


def run_bot(token=None):
    from .telegram_bot import run_bot as _run
    return _run(token)


def format_briefing(briefing, stories):
    from .telegram_formatter import format_briefing as _fmt
    return _fmt(briefing, stories)


def format_story(story):
    from .telegram_formatter import format_story as _fmt
    return _fmt(story)
