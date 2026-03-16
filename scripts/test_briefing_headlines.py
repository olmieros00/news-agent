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
    print(f"--- Top headlines (up to {len(stories)}) ---")
    for i, story in enumerate(stories, 1):
        print(f"  {i:2}. {story.headline[:75]}{'...' if len(story.headline) > 75 else ''}")
        print(f"      story_id={story.story_id}")
    print("\nTo expand a story, run: python3 scripts/test_expand_story.py <index_or_story_id>")
    print("  e.g. python3 scripts/test_expand_story.py 3")
    print("  e.g. python3 scripts/test_expand_story.py abc123def456...")


if __name__ == "__main__":
    main()
