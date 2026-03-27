# Full test: print every story with all business signal fields.
# Run from news-agent: python3 scripts/test_full_briefing.py
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
    print(f"=== Business signals briefing: {briefing.date} ({len(stories)} stories) ===\n")
    for i, story in enumerate(stories, 1):
        print("=" * 60)
        print(f"  #{i}")
        if story.priority:
            print(f"  Priority:    {story.priority} (high = B2C/retail/D2C)")
        if story.company:
            print(f"  Company:     {story.company}")
        if story.vertical:
            print(f"  Vertical:    {story.vertical}")
        if story.signal_type:
            print(f"  Signal:      {story.signal_type}")
        print(f"  Date:        {story.date}")
        print(f"  Source:      {story.source}")
        print("=" * 60)
        print(f"\n  {story.headline}\n")
        print(f"  {story.body}\n")
    print("Done.")


if __name__ == "__main__":
    main()
