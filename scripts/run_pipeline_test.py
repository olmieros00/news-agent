# Quick pipeline test: raw -> normalize -> dedupe -> cluster -> rank -> generate -> save briefing.
# Run from project root: cd news-agent && python3 scripts/run_pipeline_test.py
from __future__ import annotations

import sys
import uuid
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from config import get_source_registry
from pipeline import normalize, dedupe, cluster, rank, generate_stories
from storage import SQLiteBackend
from storage.briefing_store import save_briefing, get_latest_briefing
from models.raw import RawRecord
from models.briefing import MorningBriefing
from datetime import datetime


def main() -> None:
    backend = SQLiteBackend(":memory:")
    backend.insert_raw([
        RawRecord(
            id="r1",
            source_id="guardian",
            fetched_at=datetime.utcnow(),
            payload={
                "webUrl": "https://example.com/1",
                "webTitle": "Test 1",
                "webPublicationDate": "2025-03-14T10:00:00Z",
                "fields": {"trailText": "Body 1"},
            },
        ),
        RawRecord(
            id="r2",
            source_id="bbc_news",
            fetched_at=datetime.utcnow(),
            payload={
                "link": "https://bbc.com/2",
                "title": "Test 2",
                "summary": "Snippet 2",
                "published_parsed": (2025, 3, 14, 9, 0, 0, 0, 0, 0),
            },
        ),
    ])
    raw = backend.read_raw()
    n = normalize(raw)
    d = dedupe(n)
    c = cluster(d)
    r = rank(c, d, top_n=5)
    stories = generate_stories(r, d, get_source_registry())
    briefing = MorningBriefing(
        briefing_id=uuid.uuid4().hex,
        date="2025-03-14",
        story_ids=[s.story_id for s in stories],
    )
    save_briefing(briefing, stories, backend=backend)
    b2, s2 = get_latest_briefing(backend=backend)

    print("Pipeline test:")
    print(f"  raw={len(raw)} normalized={len(n)} deduped={len(d)} clusters={len(c)} top={len(r)}")
    print(f"  stories generated={len(stories)} briefing saved and read back: {b2 is not None and len(s2) == len(stories)}")
    if s2:
        print(f"  first story headline: {s2[0].headline}")
    print("OK")


if __name__ == "__main__":
    main()
