# Expand a single story by index (1 to N) or story_id.
# Run from news-agent: python3 scripts/test_expand_story.py <index_or_story_id>
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
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/test_expand_story.py <index_or_story_id>")
        sys.exit(1)
    arg = sys.argv[1].strip()
    briefing, stories = get_latest_briefing()
    if not briefing or not stories:
        print("No briefing found. Run the full pipeline first: python3 scripts/run_full_pipeline.py")
        sys.exit(1)
    story = None
    if arg.isdigit():
        idx = int(arg)
        if 1 <= idx <= len(stories):
            story = stories[idx - 1]
    if not story:
        for s in stories:
            if s.story_id == arg:
                story = s
                break
    if not story:
        print(f"No story found for '{arg}' (use index 1-{len(stories)})")
        sys.exit(1)

    print(f"{'='*60}")
    if story.company:
        print(f"  Company:     {story.company}")
    if story.vertical:
        print(f"  Vertical:    {story.vertical}")
    if story.signal_type:
        print(f"  Signal:      {story.signal_type}")
    print(f"  Date:        {story.date}")
    print(f"  Source:      {story.source}")
    print(f"{'='*60}")
    print(f"\n{story.headline}\n")
    print(story.body)
    print()


if __name__ == "__main__":
    main()
