# Full test: load latest briefing and print every story's headline, date, body, and bias.
# Run from news-agent: python3 scripts/test_full_briefing.py
# Requires a saved briefing first: python3 scripts/run_full_pipeline.py [--no-fetch]
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
        sys.exit(1)
    print(f"=== Full briefing: {briefing.date} ({len(stories)} stories) ===\n")
    for i, story in enumerate(stories, 1):
        print("=" * 60)
        print(f"Story {i} | story_id={story.story_id}")
        print("=" * 60)
        print("[Headline]")
        print(story.headline)
        print()
        print("[Date]")
        print(story.date)
        print()
        print("[Body]")
        print(story.body)
        print()
        print("[Bias]")
        print(story.bias)
        print()
    print("Done.")


if __name__ == "__main__":
    main()
