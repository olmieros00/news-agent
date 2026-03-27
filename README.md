# Morning News Agent

Modular pipeline: fetch → ingest → normalize → translate → dedupe → cluster → rank → generate.

## Sections

- **config/** — Source registry, prompts, runtime settings. No fetching, no pipeline.
- **connectors/** — Fetch raw from Guardian, RSS, GDELT, NewsAPI. No normalization or storage.
- **models/** — Data shapes (raw, normalized, cluster, briefing). No I/O.
- **ingestion/** — Store and read raw items only. No normalization or dedupe.
- **pipeline/** — normalize → translate → dedupe → cluster → rank → generate; orchestrate. No fetch.
- **storage/** — SQLite backend and briefing store. No pipeline logic.
- **tests/** — Unit and integration tests, fixtures.
- **scripts/** — Thin entrypoints for running and testing the pipeline.

## Phases

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Core ingestion skeleton (connectors + raw store) | Done |
| 2 | Normalization + storage | Done |
| 3 | Dedupe + clustering | Done |
| 4 | Ranking (weighted: 60% coverage, 25% diversity, 15% recency) | Done |
| 5 | Story generation (LLM headline/body/bias; non-LLM fallback) | Done |
| 6 | Scheduling + deployment | Next |

## Setup

Copy `.env.example` to `.env` and fill in API keys and DB path.

**Always run from `news-agent/`** so that `config`, `models`, `storage`, etc. are importable directly:

```bash
cd "/Users/eros.olmi/News Project/news-agent"
```

**Install dependencies:**

```bash
pip3 install -r requirements.txt
```

Installs: `python-dotenv`, `requests`, `feedparser`, `scikit-learn`, `langdetect`, `deep-translator`, `openai`.

- Without `scikit-learn`: clustering falls back to one-item-per-cluster.
- Without `langdetect` / `deep-translator`: non-English articles are not translated before clustering.
- Without `openai` / `OPENAI_API_KEY`: LLM headline/body/bias generation is skipped; rule-based fallbacks are used.

## Environment Variables (`.env`)

| Variable | Default | Description |
|---|---|---|
| `GUARDIAN_API_KEY` | — | Required for Guardian connector |
| `OPENAI_API_KEY` | — | Optional; enables LLM headline/body/bias |
| `DB_PATH` | `./news.db` | SQLite database file path |
| `TOP_N_STORIES` | `10` | Max stories in each morning briefing |
| `PIPELINE_HOURS_LOOKBACK` | `24` | How many hours back to read raw items |
| `PIPELINE_MAX_ITEMS` | `3000` | Cap on items fed into the expensive pipeline steps |
| `DB_KEEP_DAYS` | `3` | Raw items older than this are pruned on each run |

## Running the pipeline

### Full pipeline (fetch + process + save briefing)

```bash
python3 scripts/run_full_pipeline.py
```

Flags:
- `--no-fetch` — skip fetching; use existing DB (useful for re-ranking without new downloads)
- `--quick` — cap pipeline at 800 items for fast local testing

### Review hottest headlines (with score breakdown)

Runs normalize → translate → dedupe → cluster → rank on existing DB data and prints the top stories with coverage metrics. No fetch, no LLM calls, no save.

```bash
python3 scripts/test_review_hottest.py
```

Expected output per story: `coverage=`, `regions=`, `recency=`, `score=`, `latest=` (UTC).

### Show briefing headlines (from last saved briefing)

```bash
python3 scripts/test_briefing_headlines.py
```

Expected: up to 10 headlines (only stories covered by 3+ publishers). Use index or `story_id` for the expand test.

### Expand one story (date, body, bias)

```bash
python3 scripts/test_expand_story.py 3
# or
python3 scripts/test_expand_story.py <story_id>
```

Expected: headline, then **[date]**, **[body]**, **[bias]**.

### Full briefing (all stories, all fields)

```bash
python3 scripts/test_full_briefing.py
```

Prints every story in the latest briefing with headline, date, body, and bias.

## Ranking logic

Stories are ranked by a weighted score:

```
score = 0.60 × coverage + 0.25 × region_diversity + 0.15 × recency
```

- **coverage**: number of distinct publishers reporting the same event.
- **region_diversity**: number of distinct regional source groups in the cluster.
- **recency**: exponential decay with a 12-hour half-life.
- Stories with fewer than 3 publishers are excluded.
- Niche topics (sports, obituaries, live blogs, local events) are down-ranked.

## Clustering logic

Articles are grouped into one cluster per event using:
1. **TF-IDF cosine similarity** (threshold: 0.30) on title + body snippet (English text).
2. **Title keyword overlap** — if 4+ meaningful words match across titles within 24 hours, articles are merged.
3. **Time window** — articles more than 24 hours apart are never merged.
4. **Performance**: items are pre-sorted by publish date; the inner loop breaks early once the time window is exceeded, reducing comparisons significantly for large datasets.

## Headline generation

- **With `OPENAI_API_KEY`**: LLM writes a neutral, unbiased headline from scratch.
- **Without key (fallback)**: the system identifies words that appear in multiple source titles (consensus vocabulary), picks the most representative source title, and reconstructs a headline by keeping only the consensus words in their original order (preserving grammar and proper nouns).

## Progress

See **STEPS.md** for step-by-step progress log.
