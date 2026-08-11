# PR Response Doc — CineLog Watchlist Feature


## AI Usage
I used Claude throughout this project to: explain the existing codebase patterns (`add_to_collection`, deduplication logic, naming conventions) before making changes for Comments 1-3, so my changes matched existing patterns rather than introducing new ones. For Comments 4 and 5, I formed my own position first, then used AI to help me phrase my reasoning clearly and structure it into the PR Response Doc format — the actual positions (private-by-default visibility, and supporting multiple sort orders defaulting to date_added) were my own judgment calls based on the tradeoffs described. I also used AI step-by-step guidance for the git rebase and interactive rebase commands, since I hadn't done a live merge conflict resolution before, and to help debug some terminal/editor issues (accidentally running Python code as PowerShell commands, and getting stuck in Vim) that came up along the way.

Update for this revision: after review flagged that `get_watchlist` ended in a bare `return`, I gave Claude the function and asked what a caller would actually receive and which of my existing tests would have caught it. The answer that mattered wasn't the typo — which I'd already spotted — but that every test I'd written asserted on a raised exception and none asserted on a return value, which is why the whole success path was uncovered. I wrote the new `get_watchlist` tests off that observation. I also asked it to check my `git log --oneline` output against the conventional commits spec, and verified the flagged items against the spec myself rather than taking the answer on faith. The design positions in Comments 4 and 5 are unchanged from my original submission and remain my own.

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
**What conflicted:** `.gitignore` (both branches independently added one — trivial add/add conflict) and `models.py` (main had migrated `Film.id` from integer to UUID string, but my `WatchlistEntry.film_id` column was still typed as `db.Integer`).
**How I resolved it:** For `.gitignore`, merged both versions into one file containing all needed entries. For `models.py`, kept my `WatchlistEntry` class but changed `film_id` from `db.Column(db.Integer, ...)` to `db.Column(db.String(36), ...)` to match the UUID foreign key on `Film.id`. Also updated a stale docstring in `services/watchlist_service.py` that still described `film_id` as an integer.
**How I verified no conflict remains:** Ran `git rebase --continue` after resolving each conflict until the rebase completed with "Successfully rebased and updated refs/heads/feature/watchlist." Ran the full test suite (`pytest tests/ -v`) afterward — all 5 tests pass, confirming the UUID fix works correctly end to end.

## Follow-up fix — `get_watchlist` returned `None`

Flagged in review after the first submission: `get_watchlist` ended with a bare `return` instead of `return result`, so it discarded the list it had just built and always returned `None` regardless of what was in the database. My existing tests didn't catch it because all of them exercised `add_to_watchlist`'s error paths — the nonexistent-film case — and none of them ever called `get_watchlist` and asserted on what came back.

That's the more useful lesson than the typo itself. A test that only covers the raise path proves the function fails correctly; it says nothing about whether it succeeds correctly. I've since added `test_get_watchlist_empty_returns_empty_list`, `test_get_watchlist_returns_saved_films_newest_first`, and `test_get_watchlist_sort_by_title`, which assert on actual return values and would have caught this immediately.

Fixing the bare `return` exposed a second problem underneath it: `get_watchlist` builds each result from `entry.film`, but `WatchlistEntry` had no `film` relationship. `Film` declared `collection_entries` with `backref="film"` and nothing equivalent for the watchlist, so `entry.film` would have raised `AttributeError` as soon as the function actually reached a non-empty result. I added `Film.watchlist_entries` and `User.watchlist_entries` mirroring the collection relationships. I also added the `unique_user_film_watchlist` constraint to `WatchlistEntry`, matching `unique_user_film_collection` — Comment 2's dedup check is now backed at the database level the same way the collection's is, rather than relying on application code alone.

## Note on the merge commit in history

An earlier review of this PR flagged a merge commit (`bbe206c "Merge pull request #2 from ascherj/chore/add-gitignore"`) as breaking the linear-history requirement. That commit was not mine — it was the tip of the upstream `main` branch that the project instructions direct contributors to rebase onto, so it arrived as part of the base history rather than from anything I did. My own commits were, and are, fully linear.

Rather than argue the point in a PR, I've made it moot: I linearized my fork's `main` so the merge commit no longer appears anywhere in the history, then rebased `feature/watchlist` onto the linearized base. `git log --oneline` now shows a single unbroken line of commits with no merges. Anyone wanting to verify the original claim can still see it upstream with `git log --oneline upstream/main`.

## Stretch — `remove_from_watchlist()`

**What I did:** Added `remove_from_watchlist(user_id, film_id)` to `services/watchlist_service.py`, following `remove_from_collection` exactly: look up the entry by `user_id` + `film_id`, raise a dedicated `NotInWatchlistError` if it isn't there, otherwise delete, commit, and return `True`. Added the matching `DELETE /watchlist/<user_id>/remove` endpoint mirroring the collection route's shape, including its 404-on-missing behavior.

**Why it mirrors the existing pattern rather than inventing one:** the collection service already establishes that "remove" is a distinct verb with its own exception type rather than a silent no-op, and that the route translates that exception into a 404. Introducing a different convention for the watchlist — returning `False`, or deleting idempotently — would have made two sibling features behave differently for the same user mistake.

**How I verified:** `test_remove_from_watchlist_removes_entry` confirms the entry is gone and `get_watchlist` reflects it; `test_remove_from_watchlist_missing_entry_raises` confirms the error path. Both pass.

## Stretch — Second test (my choice of edge case)

**The test:** `test_get_watchlist_empty_returns_empty_list`.

**Why I chose it:** an empty watchlist is the state every brand-new user is in, so it's the highest-traffic case in the feature and the one least likely to be exercised during manual testing — when you're clicking through the app you naturally add a film first. It's also the case where the failure is quietest: `jsonify([])` and `jsonify(None)` both return `200`, so a broken empty watchlist looks fine from the outside while handing clients `null` where they expect an array. As it turned out, this is exactly the test that would have caught the bare-`return` bug above, which is a reasonable argument for writing it before you know you need it.

I also added `test_add_to_watchlist_duplicate_raises`, which asserts both that the second add raises and that only one row exists afterward — the second assertion is the one that would catch a dedup check that raises but has already written the row.

## Stretch — Visibility toggle on the endpoint

**What I did:** Added an optional `public` parameter to `add_to_watchlist()` (defaulting to `False`) and exposed it through `POST /watchlist/<user_id>/add` as an optional `public` field in the request body. The endpoint rejects non-boolean values with a `400` rather than coercing them, so `"public": "yes"` fails loudly instead of silently making a list public.

**How this relates to Comment 4:** the private-by-default decision I argued for is only defensible if opting in is genuinely easy. Without this parameter, a user who wants to share a film has to add it privately and then mutate it through some other path that doesn't exist yet. Making `public` settable at add time is what turns "private by default" into a real default rather than a hard limit, and it directly addresses the maintainer's concern that privacy-by-default would starve the discovery feature.

**How I verified:** `test_add_to_watchlist_defaults_to_private` and `test_add_to_watchlist_accepts_explicit_public_flag` cover both branches.

## PR Description

### What this feature does

CineLog already let users log films they'd **watched** (the collection). This PR adds the other half: a **watchlist** for films a user wants to watch later.

A user can save a film to their watchlist, view everything they've saved, and remove a film once they've watched it or changed their mind. Saving the same film twice is rejected rather than silently creating a duplicate row, and saving a film ID that doesn't exist returns a clear `404` instead of a database error. Each saved film can be private (the default) or public, so users can opt in to sharing their watchlist with the CineLog community.

The feature is deliberately built as a mirror of the existing collection feature — same service-layer structure, same exception-per-failure-mode convention, same route shapes — so that anyone who already knows how the collection works knows how the watchlist works.

**Endpoints added:**

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/watchlist/<user_id>` | List saved films. Optional `?sort=title`; default is newest first. |
| `POST` | `/watchlist/<user_id>/add` | Save a film. Body: `{"film_id": "<uuid>", "public": false}` — `public` optional. |
| `DELETE` | `/watchlist/<user_id>/remove` | Remove a saved film. Body: `{"film_id": "<uuid>"}` |

### Design decisions

**1. Watchlist entries are private by default (`public=False`).**

I changed the default from `public=True`. A new user saving films doesn't necessarily realize "public" means visible to strangers, and the cost of the two possible mistakes is lopsided: a user who wanted to share and didn't can fix it in one click, while a user who didn't want to share and did has already been exposed. I'd rather the default be the recoverable mistake.

The tradeoff is real and I want to name it plainly: this weakens the community discovery angle the maintainer wanted, because most users never change a default. My answer is the visibility toggle in this PR — `public` is settable at add time, so opting in costs one field rather than a separate trip through a settings screen that doesn't exist yet. If discovery still looks starved once there's usage data, the honest next step is a prompt at the point of sharing, not a quieter default.

**2. The watchlist supports multiple sort orders, defaulting to `date_added` (newest first).**

The original implementation sorted alphabetically. That's inconsistent with `get_collection`, which sorts newest-first, and inconsistency between two sibling views is a worse problem than either sort order being wrong. So the default is now `date_added`, matching the rest of the app.

But the maintainer's point about alphabetical browsing holds for large watchlists — a watchlist is a queue you scan for something to watch tonight, and past a certain size "what did I add recently" stops being the only question you're asking. So rather than picking a winner, `GET /watchlist/<user_id>` accepts `?sort=title`. The default answers the common case consistently; the parameter covers the case the maintainer raised.

### How to test this manually

The app has no frontend — `http://127.0.0.1:5000` returns a 404, which is expected. Exercise it with `curl`.

```bash
# 1. Set up and start the app
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate.bat
pip install -r requirements.txt
python app.py                      # runs at http://127.0.0.1:5000

# 2. In a second terminal, grab a real film UUID and a user UUID
curl http://127.0.0.1:5000/films

# 3. Save a film to the watchlist (defaults to private)
curl -X POST http://127.0.0.1:5000/watchlist/<user_id>/add \
     -H "Content-Type: application/json" \
     -d '{"film_id": "<film_uuid>"}'
# Expect 201 and an entry with "public": false

# 4. Save a second film, this time shared
curl -X POST http://127.0.0.1:5000/watchlist/<user_id>/add \
     -H "Content-Type: application/json" \
     -d '{"film_id": "<other_film_uuid>", "public": true}'
# Expect 201 and "public": true

# 5. View the watchlist — newest first by default
curl http://127.0.0.1:5000/watchlist/<user_id>
# Expect both films, most recently added first

# 6. View it alphabetically
curl "http://127.0.0.1:5000/watchlist/<user_id>?sort=title"
# Expect the same two films ordered A-Z

# 7. Try adding the same film twice (deduplication)
curl -X POST http://127.0.0.1:5000/watchlist/<user_id>/add \
     -H "Content-Type: application/json" \
     -d '{"film_id": "<film_uuid>"}'
# Expect 409 "already in this user's watchlist"

# 8. Try a film ID that doesn't exist
curl -X POST http://127.0.0.1:5000/watchlist/<user_id>/add \
     -H "Content-Type: application/json" \
     -d '{"film_id": "00000000-0000-0000-0000-000000000000"}'
# Expect 404 "No film found with id ..."

# 9. Remove a film
curl -X DELETE http://127.0.0.1:5000/watchlist/<user_id>/remove \
     -H "Content-Type: application/json" \
     -d '{"film_id": "<film_uuid>"}'
# Expect 200 "Removed from watchlist"

# 10. Remove it again
# Expect 404 "not in this user's watchlist"

# 11. Empty watchlist returns [], not null
curl http://127.0.0.1:5000/watchlist/<some_user_with_nothing_saved>
# Expect []
```

Automated coverage: `pytest tests/ -v` — the watchlist suite covers the nonexistent-film error, deduplication, the private default, the explicit `public` flag, empty and populated `get_watchlist`, both sort orders, and both `remove_from_watchlist` paths.

## Commit history

`git log --oneline` on `feature/watchlist`, after the interactive rebase and the
linearization described above. Eighteen commits, every one in conventional format,
no merge commits anywhere in the history:

```
b8d98c4 docs: add PR description, stretch write-ups, and get_watchlist follow-up
c8c86e8 test: cover get_watchlist return values, dedup, visibility, and removal
4af117a feat: allow callers to set watchlist visibility when adding a film
613afe2 feat: add remove_from_watchlist service function and endpoint
d81a72a fix: return the watchlist result list from get_watchlist
10efabe docs: update film_id docstring to reflect UUID type post-rebase
7331430 docs: add response for Comment 5 sort order decision
11b10ed feat: support multiple sort orders for watchlist, default to date_added
746e879 fix: default watchlist visibility to private and use UUID for film_id
f4bb0f1 test: add test for add_to_watchlist nonexistent film case
c2b3055 feat: add deduplication check to add_to_watchlist
44d716d fix: rename save_to_watchlist to add_to_watchlist for naming convention
cd166bb chore: add .gitignore
dbd586d fix: update film retrieval method to use db.session.get in collection and watchlist services
65cea66 feat: add watchlist model and endpoint
718a9a8 (main) chore: add .gitignore for generated files
07ca580 refactor: migrate film IDs from integer to UUID
014ae54 feat: initial CineLog API with film collection feature
```

The last three commits are the upstream base. Everything above `718a9a8` is this PR.
`git log --merges --oneline` returns nothing.