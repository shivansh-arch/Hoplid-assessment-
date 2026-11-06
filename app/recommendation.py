
# app/recommendation.py


# Scoring weights
CUISINE_WEIGHT = 0.50
PRICE_WEIGHT = 0.20
POPULARITY_WEIGHT = 0.15
RATING_WEIGHT = 0.15


def score_items(user, items):
    """
    Rank food items based on user preferences.

    Scoring components:
        Cuisine match: 0.50
        Price fit:     0.20
        Popularity:    0.15
        Rating:        0.15

    Returns:
        List of item dictionaries sorted by score descending.
    """

    results = []

    # Step 1: Get recently viewed item IDs.
    recent_views = set(user["recent_views"])

    # Step 2: Filter recently viewed items BEFORE scoring.
    filtered_items = [
        item for item in items
        if item["item_id"] not in recent_views
    ]

    # Step 3: Calculate scores for remaining items.
    for item in filtered_items:

        # Cuisine affinity: roughly -3 to +3.
        cuisine_score = user["food_affinity"].get(item["cuisine"], 0.0) / 3.0

        # Price fit: exact match = 1, otherwise 0.
        price_score = (
            1.0
            if item["price_level"] == user["price_pref"]
            else 0.0
        )

        # Normalize popularity to 0-1.
        popularity_score = item["popularity"] / 100.0

        # Normalize rating to 0-1.
        rating_score = item["rating"] / 5.0

        # Weighted sum.
        final_score = (
            cuisine_score * CUISINE_WEIGHT
            + price_score * PRICE_WEIGHT
            + popularity_score * POPULARITY_WEIGHT
            + rating_score * RATING_WEIGHT
        )

        # Preserve original item fields and add score.
        results.append({
            **item,
            "score": round(final_score, 4)
        })

    # Step 4: Sort highest-scoring items first.
    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )

    return results
