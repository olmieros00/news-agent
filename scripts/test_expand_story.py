# Test: expand a single story by index (1 to N) or story_id and print [date], [body], [bias].
# Run from news-agent: python3 scripts/test_expand_story.py <index_or_story_id>
#   e.g. python3 scripts/test_expand_story.py 3
#   e.g. python3 scripts/test_expand_story.py abc123def456...
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
        print("  index: 1-N (position in the top headlines list)")
        print("  story_id: exact id from test_briefing_headlines.py")
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
        print(f"No story found for '{arg}' (use index 1-{len(stories)} or a story_id from test_briefing_headlines.py)")
        sys.exit(1)
    print("--- Headline ---")
    print(story.headline)
    print()
    print("--- Date ---")
    print(story.date)
    print()
    print("--- Body ---")
    print(story.body)
    print()
    print("--- Bias ---")
    print(story.bias)


if __name__ == "__main__":
    main()
