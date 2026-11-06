# Hoplid Technical Assessment

## Architecture
[The data flow diagram I gave you early on: 
GET /recommendations, /matches, /cards, POST /feedback → 
feature_store (shared dict) → three engines → response]

One sentence: "All three engines read from and write to one shared 
feature_store, rather than maintaining separate models — this is 
what makes a food preference change propagate into matching and 
card results."

## Shared Feature Layer
The user_features schema (food_affinity, price_pref, location, 
interest_tags, recent_views, last_updated) — and why food_affinity 
specifically is the interconnection point: it's read by both 
recommendation.py and matching.py directly.

## Scoring Decisions
- Recommendation weights (cuisine 0.5, price 0.2, popularity 0.15, 
  rating 0.15) — and WHY you normalized cuisine to -1..1 (so weights 
  reflect actual intended influence, not scale artifacts)
- Matching weights (food affinity 0.625, interests 0.375) — and why 
  location became a hard filter, not a weighted component (product 
  reasoning: can't dine together across cities)
- Feedback weights (like +1.0, dislike -1.5, view +0.1, skip -0.2) — 
  and the asymmetric-cost reasoning for dislike > like

## Optimization Decisions
- O(1) item lookup index (built once in init_store, not scanned per call)
- Filter before score in both recommendation (recent_views) and 
  matching (self + location) — avoid expensive cosine similarity 
  on candidates that'll be excluded anyway
- Dynamic score normalization in card_rolling (min/max of current 
  batch, not hardcoded) — stays correct if weights change later
- response_time_ms on every endpoint
- Not implemented, but identified: caching per-user scored results 
  with a short TTL, invalidated on feedback — would help under real 
  traffic since scores are recomputed from scratch per request now

## Demonstration
[Your before/after cards.json comparison — the Indian-affinity-rise 
+ U97 compatibility-drop story]

## Scaling for Production
Short paragraph: move feature_store to Redis/Postgres, add a proper 
vector index (FAISS) for matching at scale instead of O(n) candidate 
scoring, add caching layer, async/background feature updates instead 
of synchronous feedback writes.

## Setup
pip install -r requirements.txt
uvicorn app.api:app --reload
pytest tests/ -v