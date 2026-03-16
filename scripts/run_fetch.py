# Step 6: run fetch from all usable sources and store raw items.
# Run from project root: cd news-agent && python3 scripts/run_fetch.py
from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root (news-agent) is on path
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(_root / ".env")
except ImportError:
    pass

from ingestion import fetch_and_store_all, read_raw


def main() -> None:
    items = fetch_and_store_all()
    print(f"Fetched and stored {len(items)} raw items.")
    # Verify: read back from store (uses default backend from settings)
    stored = read_raw()
    print(f"Verify: {len(stored)} raw records in store.")


if __name__ == "__main__":
    main()
