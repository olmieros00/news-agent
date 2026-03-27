# Test: load latest briefing and print the top headlines (up to 10; only stories with 3+ articles).
# Run from news-agent: python3 scripts/test_briefing_headlines.py
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

from storage.briefing_store import get_latest_briefing


def main() -> None:
    briefing, stories = get_latest_briefing()
    if not briefing or not stories:
        print("No briefing found. Run the full pipeline first: python3 scripts/run_full_pipeline.py")
        return
    print(f"Latest briefing: {briefing.date} ({len(stories)} stories)\n")
    high = [s for s in stories if s.priority == "high"]
    standard = [s for s in stories if s.priority != "high"]

    if high:
        print(f"--- B2C / Retail / D2C ({len(high)}) ---")
        for i, story in enumerate(high, 1):
            signal = f"[{story.signal_type}]" if story.signal_type else ""
            print(f"  {i:2}. {signal:14s} {story.company:20s}  {story.headline[:55]}{'...' if len(story.headline) > 55 else ''}")
            print(f"      Vertical: {story.vertical}  |  Source: {story.source}")

    if standard:
        offset = len(high)
        print(f"\n--- Other verticals ({len(standard)}) ---")
        for i, story in enumerate(standard, 1):
            signal = f"[{story.signal_type}]" if story.signal_type else ""
            print(f"  {offset+i:2}. {signal:14s} {story.company:20s}  {story.headline[:55]}{'...' if len(story.headline) > 55 else ''}")
            print(f"      Vertical: {story.vertical}  |  Source: {story.source}")

    print(f"\nTo expand a story: python3 scripts/test_expand_story.py <number>")


if __name__ == "__main__":
    main()
