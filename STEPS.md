# Implementation steps — progress tracker

Use this to continue step-by-step. Each step is independently buildable and testable.

---

## Step 1 — Config: settings — **DONE**

- [x] `config/settings.py`: load from env (`python-dotenv` + `os.getenv`)
- [x] `Settings`: `guardian_api_key`, `newsapi_key`, `db_path`, `telegram_bot_token`, `openai_api_key`, `top_n_stories`, `pipeline_hours_lookback` (default 8h), `pipeline_max_items`, `db_keep_days`
- [x] `get_settings()` caches on first call

---

## Step 2 — Storage: backend interface + SQLite — **DONE**

- [x] `storage/backend.py`: abstract `Backend` with `insert_raw`, `read_raw`, `prune_raw`, `save_briefing`, `get_latest_briefing`
- [x] `storage/sqlite.py`: `SQLiteBackend`, tables: `raw_items`, `briefings`, `stories`; `prune_raw` deletes rows older than cutoff
- [x] `storage/__init__.py`: export `SQLiteBackend`

---

## Step 3 — Ingestion: raw_store — **DONE**

- [x] `ingestion/raw_store.py`: `write_raw(items, backend)`, `read_raw(source_id, since, until, backend)`
- [x] `ingestion/fetch_and_store.py`: `fetch_and_store_all()` — Guardian + all usable RSS sources

---

## Steps 4–5 — Connectors: Guardian + RSS — **DONE**

- [x] `connectors/guardian.py`: Guardian Content API, paginated, timeout=30
- [x] `connectors/rss.py`: generic RSS/Atom via feedparser; 15s timeout via requests; calendar.timegm for UTC date parsing
- [x] 30+ sources across 6 regions; 5 disabled (AP, Telegraph, Arab News, Daily Nation — blocked/paywalled; Politico EU updated to `/feed/`)

---

## Step 7 — Pipeline: normalize — **DONE**

- [x] `pipeline/normalize.py`: raw → NormalizedItem (Guardian + RSS); calendar.timegm for date; HTML stripped from RSS summaries; media prefixes stripped (WATCH:/LISTEN:/VIDEO: etc.)

---

## Steps 9–11 — Dedupe, cluster, rank — **DONE**

- [x] `pipeline/dedupe.py`: exact by URL, near-dupe by normalized title
- [x] `pipeline/cluster.py`: TF-IDF + cosine similarity (threshold=0.30) + title-word overlap (≥4 words); 24h time window; union-find; pre-sorted by date with early-break optimisation; **per-source dedup** (one article per publisher per cluster — coverage = distinct publishers)
- [x] `pipeline/rank.py`:
  - Score = **0.65×coverage + 0.25×regions + 0.10×recency** (36h half-life)
  - Eligibility: **coverage ≥ 3** distinct publishers + **regions ≥ 2** + **at least one anchor region** (western / european / middle_eastern)
  - Niche filter: sports, live blogs, obituaries, seasonal/calendar, horoscopes, LATAM financial/local, listicles, media-format labels
  - Relevance filter applied before scoring

---

## Steps 12–13 — Generate + briefing store — **DONE**

- [x] `config/prompts.py`: headline (6 rules: English only, no copy, no prefixes, 6–12 words) / body / bias prompt templates
- [x] `pipeline/generate.py`: LLM headline + body + bias (OpenAI gpt-4o-mini); fallback = shortest clean English title from cluster (5–12 word range); LLM errors logged; **output language guard** on headline and body (`_ensure_english` via langdetect + GoogleTranslator)
- [x] `pipeline/translate.py`: non-EN detection + translation (langdetect + deep-translator); parallel (4 workers); ASCII bypass on body only (not titles — catches Spanish/French/Italian ASCII titles)
- [x] `storage/briefing_store.py`: `save_briefing`, `get_latest_briefing`

---

## Step 14 — Orchestrate — **DONE**

- [x] `pipeline/orchestrate.py`: `run_pipeline(backend, fetch, since, until, hours_lookback, max_items, top_n_stories)` — full pipeline in one call; prunes old raw on each run; `until` computed after fetch (fixes empty-DB-on-first-run bug); returns `PipelineResult`
- [x] `scripts/run_full_pipeline.py`: thin wrapper (`--no-fetch`, `--quick` at 1600 items)
- [x] Test scripts: `test_review_hottest.py`, `test_briefing_headlines.py`, `test_expand_story.py`, `test_full_briefing.py`
- [x] `TESTS.md`: full test reference with copy-paste commands

---

## Steps 15–16 — Telegram + scheduling — **NEXT**

- [ ] `delivery/telegram_formatter.py`: format Story → Telegram message (headline list, drill-down)
- [ ] `delivery/telegram_bot.py`: `/morning` command, inline buttons, story drill-down
- [ ] `scripts/run_bot.py`: start Telegram bot
- [ ] Scheduling: cron / Cloud Scheduler → `run_pipeline()` daily
- [ ] Deployment: Google Cloud (Cloud Run or VM) for bot + scheduler
