# Full pipeline: fetch (optional) + process -> save briefing. Delegates to pipeline.run_pipeline().
# Run: python3 scripts/run_full_pipeline.py [--no-fetch] [--quick]
from __future__ import annotations

import argparse
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

try:
    import feedparser  # noqa: F401
except ImportError:
    print("Missing dependency: feedparser. Install with: pip3 install -r requirements.txt")
    sys.exit(1)
try:
    import sklearn  # noqa: F401
except ImportError:
    print("Missing dependency: scikit-learn. Install with: pip3 install scikit-learn")
    sys.exit(1)

from config import get_settings
from pipeline import run_pipeline
from storage import SQLiteBackend
from storage.briefing_store import get_latest_briefing


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full pipeline (fetch + process) or process only (--no-fetch).")
    parser.add_argument("--no-fetch", action="store_true", help="Skip fetch; use existing DB only.")
    parser.add_argument("--quick", action="store_true", help="Use 800 items max for faster run (e.g. testing headlines).")
    args = parser.parse_args()
    settings = get_settings()
    backend = SQLiteBackend(settings.db_path)

    if not args.no_fetch:
        print("1. Fetching from Guardian + RSS...")
    else:
        print("1. Skipping fetch (--no-fetch); using existing DB.")
    print("2. Reading raw -> normalize -> translate -> dedupe -> cluster -> rank -> generate -> save briefing...")

    result = run_pipeline(
        backend,
        fetch=not args.no_fetch,
        hours_lookback=settings.pipeline_hours_lookback,
        max_items=1600 if args.quick else None,
        top_n_stories=settings.top_n_stories,
    )

    if result is None:
        print("   No raw items. Run without --no-fetch first (needs GUARDIAN_API_KEY and network), or check DB.")
        return

    print(f"   Read {result.raw_count} raw; normalized {result.normalized_count}; deduped {result.deduped_count}; clusters {result.cluster_count}; ranked {result.ranked_count}.")
    print(f"   Saved briefing with {len(result.stories)} stories.")

    b, s = get_latest_briefing(backend=backend)
    if b and s:
        print(f"\n--- Latest briefing ({len(s)} headlines) ---")
        for i, story in enumerate(s, 1):
            print(f"  {i}. {story.headline[:70]}{'...' if len(story.headline) > 70 else ''}")
    print("Done.")


if __name__ == "__main__":
    main()
