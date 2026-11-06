# Hoplid — Matching & Recommendation Intelligence System

A prototype interconnected system with three engines (Recommendation, Matching,
Card Rolling) that share one central feature store, so a single piece of user
feedback propagates across all three.

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1        # Windows
pip install -r requirements.txt

uvicorn app.api:app --reload     # starts server on http://127.0.0.1:8000
pytest tests/ -v                 # run tests
```

## Architecture

```
User data → Shared feature_store → Recommendation + Matching → Card Rolling
→ Feedback → Updated signals → Better recommendations/matches/cards
```

All three engines read from and write to **one shared `feature_store`**,
rather than maintaining separate preference models. This is the single
decision that makes the system interconnected rather than three isolated
scripts sharing a repo.

```
app/
├── synthetic_data.py   → generates 100 users, 50 food items, 20 restaurants, 300 interactions
├── feature_store.py    → in-memory shared store: user_features dict, item index, feedback weights
├── recommendation.py   → ranks food/restaurants per user
├── matching.py         → ranks compatible users per user
├── card_rolling.py     → merges recommendation + matching output into one feed
├── feedback.py         → thin wrapper exposing feature_store updates to the API
└── api.py              → FastAPI routes wiring everything together
```

### Request flow

```
GET /recommendations?user_id=X
  → feature_store.get_user(X) + get_items()
  → recommendation.score_items() → ranked list

GET /matches?user_id=X
  → feature_store.get_user(X) + get_all_users()
  → matching.score_users() → ranked list (reads the SAME food_affinity dict)

GET /cards?user_id=X
  → top 10 from both engines above
  → card_rolling.build_cards() → merged, deduplicated, diversity-applied feed

POST /feedback {user_id, item_id, action}
  → feature_store.update_user() mutates food_affinity + recent_views
  → next call to any GET route reflects the change
```

## Shared Feature Schema

```python
user_features = {
    "user_id": str,
    "food_affinity": {cuisine: score},   # -3 to +3, the interconnection signal
    "price_pref": "low" | "medium" | "high",
    "location": str,
    "interest_tags": [str],
    "recent_views": [item_id],           # last 15, FIFO
    "last_updated": float
}
```

`food_affinity` is the field both the Recommendation and Matching engines
read. A change here, from a single `/feedback` call, is what makes the
system react as one unit instead of three.

## Scoring Decisions

**Recommendation** (`recommendation.py`) — weighted sum:

| Signal | Weight | Notes |
|---|---|---|
| Cuisine match (`food_affinity`) | 0.50 | Normalized from -3..3 to -1..1 before weighting |
| Price fit | 0.20 | Exact match = 1, else 0 |
| Popularity | 0.15 | Normalized 0..1 |
| Rating | 0.15 | Normalized 0..1 |

Cuisine affinity was initially on a -3..+3 raw scale while the other three
signals were 0..1 — multiplying by weight alone didn't make the weights mean
what they said, since cuisine's *effective* contribution was roughly 7x larger
than intended. Normalizing all components to the same scale first ensures
each weight reflects actual intended influence, not an accident of raw scale.

**Matching** (`matching.py`) — compatibility score 0–100:

| Signal | Weight | Notes |
|---|---|---|
| Food affinity (cosine similarity) | 0.625 | Same `food_affinity` dict as Recommendation |
| Shared interests (Jaccard similarity) | 0.375 | |
| Location | hard filter, not weighted | See below |

Location was moved from a weighted component to a **hard pre-filter**: two
users in different cities can't realistically dine together, so a
95%-compatible match in another city has no product value. This also serves
as a cheap filter before the more expensive cosine similarity calculation.

**Feedback weights** (`feature_store.py`):

| Action | Weight |
|---|---|
| like | +1.0 |
| dislike | -1.5 |
| view | +0.1 |
| skip | -0.2 |

Dislike outweighs like because the costs are asymmetric: showing someone
content they explicitly rejected damages trust and wastes their attention,
while not showing something they'd have liked is only a missed opportunity.

## Optimization Decisions

- **O(1) item lookup**: `items_index` dict built once in `init_store()`,
  used by `update_user()` on every feedback call — avoids an O(n) linear
  scan over the catalogue per request.
- **Filter before scoring**: `recommendation.py` excludes `recent_views`
  before running the scoring loop; `matching.py` excludes self and
  cross-location candidates before the cosine similarity calculation. Both
  avoid spending compute on items/candidates that will be discarded anyway.
- **Dynamic score normalization**: `card_rolling.py` normalizes food scores
  using the actual min/max of the current batch rather than a hardcoded
  range, so it stays correct if `recommendation.py`'s weights are retuned
  later.
- **Latency tracking**: every endpoint returns `response_time_ms`.
- **Not implemented, identified as next step**: scores are currently
  recomputed from scratch on every request. With real traffic, I'd cache
  per-user scored results with a short TTL, invalidated on feedback.

## Minimum API

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Liveness check |
| GET | `/recommendations?user_id=X` | Top 10 ranked food items for a user |
| GET | `/matches?user_id=X` | Top 10 compatible users (same city only) |
| GET | `/cards?user_id=X` | Merged, deduplicated, diversity-applied feed |
| POST | `/feedback` | Body: `{user_id, item_id, action}` — mutates shared state |

## Demonstration

Before/after on user `U1`:

1. **Before**: feed dominated by Indian food items (`food_affinity["Indian"]`
   starting mid-range) and four candidate matches, led by `U74` at 72.9
   compatibility.
2. **Action**: liked two Indian items via `/feedback`.
3. **After**:
   - `food_affinity["Indian"]` rose to the clamp ceiling (3.0).
   - Every Indian food card's score increased (e.g. `F29`: 0.866 → 0.918).
   - **Compatibility scores shifted for users never touched directly** —
     `U97` dropped from 72.9 to 70.7 because their own `food_affinity`
     vector is now less aligned with U1's updated profile.

That compatibility shift is the clearest proof of interconnection: a food
preference signal, applied only through `/feedback`, changed the Matching
Engine's output without any direct interaction with the matching logic.

## Scaling for Production

- Move `feature_store` from an in-memory dict to Redis (hot signals) +
  Postgres (durable user/item records).
- Replace O(n) candidate scoring in `matching.py` with a vector index
  (FAISS) once user counts grow past a few thousand.
- Add a caching layer for scored results, invalidated on feedback writes.
- Move feedback processing to an async queue instead of synchronous writes,
  so `/feedback` returns immediately and signal propagation happens in the
  background.

## What Was Deliberately Left Out

Given the 3-hour build window, these were scoped out as explicitly
non-required by the assessment brief: Redis, FAISS, Docker, large-scale load
testing, and advanced ML training. Feedback updates are a simple weighted
signal adjustment rather than an online-learning model, per the brief's note
that "a well-designed signal/update mechanism is sufficient."

## Tests

```bash
pytest tests/ -v
```

4 tests covering:
- Recency filtering (items in `recent_views` never reappear)
- Same-location matching constraint
- Mixed card types (`food` and `person`) in the final feed
- The core proof that feedback changes recommendation output
