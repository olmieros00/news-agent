# How to test the News Agent

Every command below is ready to copy and paste into your terminal. Nothing to change or fill in.

---

## Before you start

Open your terminal and run this first. Every test below assumes you are already in this folder:

```
cd "/Users/eros.olmi/News Project/news-agent"
```

Make sure dependencies are installed:

```
pip3 install -r requirements.txt
```

Make sure your `.env` file exists with at least the Guardian API key:

```
GUARDIAN_API_KEY=your_key_here
```

---

## Test 1 — Run the full pipeline (downloads news + creates a briefing)

This downloads fresh news from all sources, processes everything, and saves a briefing with headlines.

Copy and paste this:

```
python3 scripts/run_full_pipeline.py --quick 2>&1
```

What you should see:
- "Fetching from Guardian + RSS..."
- "Read X raw; normalized Y; deduped Z; clusters W; ranked N."
- "Saved briefing with N stories."
- A numbered list of headlines, all in English.

If you see "No raw items", your `.env` may be missing the Guardian API key or you have no internet connection.

---

## Test 2 — See the ranking breakdown (why each story is ranked where it is)

This shows each headline with its score: how many publishers covered it, how many regions, and how recent it is.

Copy and paste this:

```
python3 scripts/test_review_hottest.py 2>&1
```

What you should see:
- Each headline with `coverage=`, `regions=`, `recency=`, `score=`
- Coverage should be 3 or more for every story shown
- Regions should be 2 or more for every story shown

You must run Test 1 at least once before this works.

---

## Test 3 — See just the headlines (clean list)

This prints the headlines from the last briefing you generated.

Copy and paste this:

```
python3 scripts/test_briefing_headlines.py 2>&1
```

What you should see:
- A numbered list of headlines (up to 10)
- Each headline has a `story_id` next to it (you'll use this in Test 4)

You must run Test 1 at least once before this works.

---

## Test 4 — Read one full story (headline + date + body + bias)

This expands one story from the briefing. Replace the number `1` with whichever story you want to read (1, 2, 3, etc. from the list in Test 3).

Copy and paste this:

```
python3 scripts/test_expand_story.py 1 2>&1
```

What you should see:
- **[Headline]** — a clean English headline
- **[Date]** — the date of the event
- **[Body]** — a 5–10 line factual summary in English
- **[Bias]** — how different regions frame the story differently

You must run Test 1 at least once before this works.

---

## Test 5 — Read ALL stories (full briefing dump)

This prints every story in the briefing with all four sections (headline, date, body, bias).

Copy and paste this:

```
python3 scripts/test_full_briefing.py 2>&1
```

What you should see:
- Every story printed with `[Headline]`, `[Date]`, `[Body]`, `[Bias]`
- Everything in English
- No empty sections

You must run Test 1 at least once before this works.

---

## Test 6 — Quick internal test (no internet needed)

This runs a small test using fake data to check the pipeline code works. No API keys or internet required.

Copy and paste this:

```
python3 scripts/run_pipeline_test.py 2>&1
```

What you should see:
- "Pipeline test:" with some counts
- "OK" at the end

---

## Test 7 — Download news only (no processing)

This downloads news from all sources and saves it to the database, but does NOT create a briefing. Useful if you just want fresh data.

Copy and paste this:

```
python3 scripts/run_fetch.py 2>&1
```

What you should see:
- "Fetched and stored N raw items."
- "Verify: N raw records in store."

---

## Speed options

You can make tests faster or slower by adding flags to Test 1:

| What you want | Command |
|---|---|
| Normal run (recommended) | `python3 scripts/run_full_pipeline.py --quick 2>&1` |
| Fast re-test (skip downloading, use existing data) | `python3 scripts/run_full_pipeline.py --no-fetch --quick 2>&1` |
| Full thorough run (slower, more data, better results) | `python3 scripts/run_full_pipeline.py 2>&1` |

---

## After changing code

If you changed any code and want to verify nothing broke, run these three in order:

**Step 1** — Quick re-run on existing data:

```
python3 scripts/run_full_pipeline.py --no-fetch --quick 2>&1
```

**Step 2** — Check rankings look right:

```
python3 scripts/test_review_hottest.py 2>&1
```

**Step 3** — Check full output looks right:

```
python3 scripts/test_full_briefing.py 2>&1
```

If you changed the news sources or connectors, also run a fresh download:

```
python3 scripts/run_full_pipeline.py --quick 2>&1
```

---

## Something went wrong?

| What happened | What to do |
|---|---|
| "No raw items" | Run Test 1 first (without `--no-fetch`) |
| "0 stories" or "ranked 0" | Not enough sources covered the same event. Try without `--quick` for more data |
| Headlines in Spanish or Italian | Check `langdetect` and `deep-translator` are installed: `pip3 install langdetect deep-translator` |
| Messy/jumbled headlines | Check `OPENAI_API_KEY` is set in `.env` and `openai` is installed: `pip3 install openai` |
| "ModuleNotFoundError" | Run `pip3 install -r requirements.txt` |
| HTTP 401/403 errors | That news source blocked access — it's skipped automatically, not a problem |
