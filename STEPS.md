# Implementation steps — progress tracker

Use this to continue step-by-step. Each step is independently buildable and testable.

---

## Step 1 — Config: settings — **DONE**

- [x] `config/settings.py`: load from env (`python-dotenv` + `os.getenv`)
- [x] `Settings`: `guardian_api_key`, `newsapi_key`, `db_path`, `telegram_bot_token`, `openai_api_key`, `top_n_stories`, `pipeline_hours_lookback`, `pipeline_max_items`, `db_keep_days`
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

---

## Step 7 — Pipeline: normalize — **DONE**

- [x] `pipeline/normalize.py`: raw → NormalizedItem (Guardian + RSS); calendar.timegm for date; HTML stripped from RSS summaries

---

## Steps 9–11 — Dedupe, cluster, rank — **DONE**

- [x] `pipeline/dedupe.py`: exact by URL, near-dupe by normalized title
- [x] `pipeline/cluster.py`: TF-IDF + cosine similarity (threshold=0.30) + title-word overlap (≥4 words); 24h time window; union-find
- [x] `pipeline/rank.py`: score = 0.60×coverage + 0.25×regions + 0.15×recency; min coverage ≥ 3; niche filter (sports/live/obituary)

---

## Steps 12–13 — Generate + briefing store — **DONE**

- [x] `config/prompts.py`: headline / body / bias prompt templates
- [x] `pipeline/generate.py`: LLM headline + body + bias (OpenAI gpt-4o-mini); fallback = consensus-word synthesis + merged snippets + region coverage list; LLM errors logged
- [x] `pipeline/translate.py`: non-EN detection + translation (langdetect + deep-translator); parallel (4 workers); ASCII-only fast path
- [x] `storage/briefing_store.py`: `save_briefing`, `get_latest_briefing`

---

## Step 14 — Orchestrate — **DONE**

- [x] `pipeline/orchestrate.py`: `run_pipeline(backend, fetch, since, until, hours_lookback, max_items, top_n_stories)` — full pipeline in one call; prunes old raw on each run; returns `PipelineResult`
- [x] `scripts/run_full_pipeline.py`: thin wrapper (`--no-fetch`, `--quick` flags)

---

## Steps 15–16 — Telegram + scheduling — **NEXT**

- [ ] `delivery/telegram_formatter.py`: format Story → Telegram message (headline list, drill-down)
- [ ] `delivery/telegram_bot.py`: `/morning` command, inline buttons, story drill-down
- [ ] `scripts/run_bot.py`: start Telegram bot
- [ ] Scheduling: cron / Cloud Scheduler → `run_pipeline()` daily
- [ ] Deployment: Google Cloud (Cloud Run or VM) for bot + scheduler
