# PR Response Doc — CineLog Watchlist Feature

## AI Usage
<!-- Fill in at the end -->

## Comment 1 — Rename
**What I did:** Renamed `save_to_watchlist` to `add_to_watchlist` in `services/watchlist_service.py` to follow the project's `verb_to_noun` naming convention (matching `add_to_collection`, `remove_from_collection`, `get_collection`). Updated the import and call site in `routes/watchlist/watchlist.py` accordingly.
**How I verified:** Ran `git grep save_to_watchlist` to confirm zero remaining references, then `git grep add_to_watchlist` to confirm all 3 expected usages were updated. Ran the full test suite (`pytest tests/ -v`) — all 4 tests pass.

## Comment 2 — Deduplication
**What I did:** Added an `AlreadyInWatchlistError` exception class and a duplicate check in `add_to_watchlist`, following the same pattern as `add_to_collection` in `collection_service.py`. Before inserting a new `WatchlistEntry`, the function now queries for an existing entry with the same `user_id` and `film_id` and raises `AlreadyInWatchlistError` if one exists.
**How I verified:** Ran the full test suite (`pytest tests/ -v`) — all 4 existing tests still pass, confirming the change didn't break existing behavior.

## Comment 3 — Missing test
**What I did:**
**How I verified:**

## Comment 4 — Default visibility
**My position:**
**Reasoning:**
**Tradeoff acknowledged:**

## Comment 5 — Sort order
**My position:**
**Reasoning:**
**Engagement with reviewer's point:**

## Comment 6 — Rebase
**What conflicted:**
**How I resolved it:**
**How I verified no conflict remains:**

## PR Description
<!-- Written at the end — feature overview, design decisions, manual testing steps -->