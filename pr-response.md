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
**What I did:** Created `tests/test_watchlist.py` following the same fixture and assertion pattern as `test_collection.py`. Added `test_add_to_watchlist_nonexistent_film_raises`, mirroring `test_add_to_collection_nonexistent_film_raises` — it confirms that calling `add_to_watchlist` with a film_id that doesn't exist raises `FilmNotFoundError` rather than a raw database error.
**How I verified:** Ran `pytest tests/test_watchlist.py -v` — test passes. Ran the full suite `pytest tests/ -v` to confirm no regressions.

## Comment 4 — Default visibility
**My position:** Changed the default for `WatchlistEntry.public` from `True` to `False`.
**Reasoning:** Privacy-by-default is safer for users. A new user adding films to their watchlist may not realize that "public" means visible to others — defaulting to private avoids ever surprising someone with unwanted exposure, and matches conventions used by most similar apps (e.g. private-by-default lists that users explicitly opt in to sharing). Users who want to participate in the community aspect can still opt in by toggling their watchlist to public.
**Tradeoff acknowledged:** This weakens the community/discovery angle the maintainer explicitly wanted the feature to support — if most users never touch the default, the social feature may see little organic use. I'm prioritizing user trust and avoiding accidental exposure over maximizing default participation in the community feature.
## Comment 5 — Sort order
**My position:** Support multiple sort orders instead of forcing one. Added a `sort_by` parameter to `get_watchlist`, exposed via a `?sort=title` query param on `GET /watchlist/<user_id>`. Default remains `date_added` (newest first) when no param is given.
**Reasoning:** Defaulting to `date_added` (newest first) keeps behavior consistent with `get_collection`, so users get the same mental model across both views. Allowing `?sort=title` still gives users the benefit of alphabetical browsing for larger watchlists, without forcing everyone into one fixed order.
**Engagement with reviewer's point:** The reviewer's original alphabetical-only implementation was inconsistent with `get_collection`'s date-based sort. Rather than picking one side, I addressed the inconsistency by making `date_added` the default (matching the rest of the app) while preserving the alphabetical option as an opt-in for users who prefer it.

## Comment 6 — Rebase
**What conflicted:**
**How I resolved it:**
**How I verified no conflict remains:**

## PR Description
<!-- Written at the end — feature overview, design decisions, manual testing steps -->