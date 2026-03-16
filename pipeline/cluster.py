# Group items into clusters (same event). Output Cluster list.
# Real clustering: TF-IDF + cosine similarity on title/snippet; time window; connected components.
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone
from typing import List

from models.cluster import Cluster
from models.normalized import NormalizedItem

# Time window: only cluster items whose published_at is within this of each other (latest 24h).
CLUSTER_TIME_WINDOW_HOURS = 24
# Min cosine similarity (title + snippet) to consider same story.
# 0.30 reduces false merges vs 0.26, while still catching same-event articles with different wording.
CLUSTER_SIMILARITY_THRESHOLD = 0.30
# If this many words are repeated in titles only, treat as same cluster (within time window).
CLUSTER_TITLE_MIN_WORDS = 4


def _aware(d: datetime) -> datetime:
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d


# Stopwords for title-word overlap (skip trivial words)
_TITLE_STOP = frozenset(
    {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "as", "is", "was", "are", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those", "it", "its", "it's"}
)


def _title_tokens(title: str) -> set[str]:
    """Tokenize title: lowercase, letters only, drop stopwords and very short tokens."""
    if not title:
        return set()
    words = re.findall(r"[a-z0-9]+", (title or "").lower())
    return {w for w in words if len(w) > 1 and w not in _TITLE_STOP}


def _union_find(n: int) -> tuple:
    """Union-Find (disjoint set). parent[i] = root index."""
    parent = list(range(n))

    def find(x: int) -> int:
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x: int, y: int) -> None:
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    return find, union


def cluster(normalized_items: List[NormalizedItem]) -> List[Cluster]:
    """
    Group articles about the same event. Merge if (within time window) either:
    (1) Cosine similarity on title+snippet >= threshold, or
    (2) Titles share at least CLUSTER_TITLE_MIN_WORDS (e.g. 4) meaningful words.
    Time window = latest 24h. Each component = one cluster.
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
    except ImportError as e:
        raise RuntimeError(
            "Real clustering requires scikit-learn. Install with: pip3 install scikit-learn"
        ) from e

    if not normalized_items:
        return []
    if len(normalized_items) == 1:
        return [Cluster(cluster_id=normalized_items[0].id, member_ids=[normalized_items[0].id])]

    # Build text for each item (use English if translated, else original) for clustering
    def _text_for_cluster(item: NormalizedItem) -> str:
        tit = (item.title_en or item.title or "").strip()
        body = (item.body_en or item.body_or_snippet or "")[:500].strip()
        return (tit + " " + body).strip() or tit

    texts = [_text_for_cluster(item) for item in normalized_items]

    vectorizer = TfidfVectorizer(max_features=5000, stop_words="english", min_df=1)
    try:
        X = vectorizer.fit_transform(texts)
    except Exception:
        # Fallback if vectorizer fails (e.g. all empty)
        return [
            Cluster(cluster_id=item.id, member_ids=[item.id])
            for item in normalized_items
        ]

    sim = cosine_similarity(X, X)
    n = len(normalized_items)
    find, union = _union_find(n)
    window_secs = CLUSTER_TIME_WINDOW_HOURS * 3600.0

    # Precompute timestamps (epoch seconds) and title token sets.
    timestamps = [_aware(normalized_items[i].published_at).timestamp() for i in range(n)]
    title_sets = [_title_tokens((normalized_items[i].title_en or normalized_items[i].title) or "") for i in range(n)]

    # Pre-sort indices by timestamp so we can break early in the inner loop.
    sorted_idx = sorted(range(n), key=lambda i: timestamps[i])

    for pos_i, i in enumerate(sorted_idx):
        ti = timestamps[i]
        for pos_j in range(pos_i + 1, n):
            j = sorted_idx[pos_j]
            tj = timestamps[j]
            # Items are sorted ascending; once gap exceeds window, no further j can match.
            if tj - ti > window_secs:
                break
            # Merge if cosine similarity (title+snippet) is high enough
            if sim[i, j] >= CLUSTER_SIMILARITY_THRESHOLD:
                union(i, j)
                continue
            # Or merge if titles share at least N meaningful words (e.g. 4)
            overlap = len(title_sets[i] & title_sets[j])
            if overlap >= CLUSTER_TITLE_MIN_WORDS:
                union(i, j)

    # Collect components: root -> list of indices
    components: dict[int, list[int]] = {}
    for i in range(n):
        root = find(i)
        components.setdefault(root, []).append(i)

    clusters = []
    for indices in components.values():
        # Per-source deduplication: keep only the most recently published item per source_id.
        # This prevents inflated coverage counts when one publisher posts many articles on the same story.
        # Coverage should equal distinct publishers, not total article count.
        seen_sources: dict[str, tuple[int, float]] = {}  # source_id -> (index, timestamp)
        for i in indices:
            src = normalized_items[i].source_id
            ts = _aware(normalized_items[i].published_at).timestamp()
            if src not in seen_sources or ts > seen_sources[src][1]:
                seen_sources[src] = (i, ts)
        deduped_indices = [idx for idx, _ in seen_sources.values()]
        member_ids = [normalized_items[i].id for i in deduped_indices]
        # Deterministic cluster_id from sorted member ids
        key = "|".join(sorted(member_ids))
        cluster_id = hashlib.sha256(key.encode()).hexdigest()[:24]
        clusters.append(Cluster(cluster_id=cluster_id, member_ids=member_ids))

    return clusters
