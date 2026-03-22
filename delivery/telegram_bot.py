# Telegram bot: /morning → headline list with inline buttons; tap → expanded story.
# Uses python-telegram-bot v21+ (async). Messages use HTML parse mode.
from __future__ import annotations

import logging
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from delivery.telegram_formatter import format_briefing, format_story

log = logging.getLogger(__name__)

_PARSE = "HTML"


def _load_briefing():
    """Load the latest briefing + stories from storage."""
    from storage.briefing_store import get_latest_briefing
    return get_latest_briefing()


async def _morning_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /morning — send headline list with inline buttons."""
    briefing, stories = _load_briefing()
    if not briefing or not stories:
        await update.message.reply_text("No briefing available yet. Run the pipeline first.")
        return

    text = format_briefing(briefing, stories)
    buttons = []
    for i, story in enumerate(stories, 1):
        label = f"{i}. {story.headline[:40]}{'…' if len(story.headline) > 40 else ''}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"story:{story.story_id}")])

    await update.message.reply_text(
        text,
        parse_mode=_PARSE,
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def _story_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button tap — send full story (date, body, bias)."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    if not data.startswith("story:"):
        return

    story_id = data[len("story:"):]
    _, stories = _load_briefing()
    story = next((s for s in stories if s.story_id == story_id), None)

    if not story:
        await query.edit_message_text("Story not found. Try /morning again.")
        return

    text = format_story(story)
    await query.message.reply_text(text, parse_mode=_PARSE)


async def _start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start — welcome message."""
    await update.message.reply_text(
        "👋 Welcome to the Morning News Agent.\n\nSend /morning to get today's briefing."
    )


async def _refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /refresh — run the pipeline and then send the briefing."""
    await update.message.reply_text("⏳ Refreshing… this takes 30–90 seconds.")

    import asyncio
    from config import get_settings
    from storage import SQLiteBackend
    from pipeline import run_pipeline

    settings = get_settings()
    backend = SQLiteBackend(settings.db_path)

    result = await asyncio.to_thread(
        run_pipeline,
        backend,
        fetch=True,
        hours_lookback=settings.pipeline_hours_lookback,
        max_items=settings.pipeline_max_items,
        top_n_stories=settings.top_n_stories,
    )

    if result is None:
        await update.message.reply_text("No stories found after refresh. Try again later.")
        return

    await update.message.reply_text(
        f"✅ Refreshed: {result.ranked_count} stories from {result.raw_count} articles."
    )
    await _morning_command(update, context)


async def _post_init(application) -> None:
    """Register bot commands on startup so the menu appears in Telegram."""
    await application.bot.set_my_commands([
        ("morning", "Get today's briefing"),
        ("refresh", "Download fresh news and rebuild briefing"),
        ("start", "Welcome message"),
    ])


def run_bot(token: Optional[str] = None) -> None:
    """Start the Telegram bot (blocking, runs until Ctrl+C)."""
    if not token:
        from config import get_settings
        token = get_settings().telegram_bot_token
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

    app = Application.builder().token(token).post_init(_post_init).build()
    app.add_handler(CommandHandler("start", _start_command))
    app.add_handler(CommandHandler("morning", _morning_command))
    app.add_handler(CommandHandler("refresh", _refresh_command))
    app.add_handler(CallbackQueryHandler(_story_callback))

    log.info("Bot starting… Send /morning in Telegram.")
    print("Bot is running. Send /morning in Telegram. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)
