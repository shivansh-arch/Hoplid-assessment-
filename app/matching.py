
FOOD_AFFINITY_WEIGHT = 0.625
INTEREST_WEIGHT = 0.375


def cosine_similarity(user_affinity, candidate_affinity):
    cuisines = sorted(
        set(user_affinity.keys()) | set(candidate_affinity.keys())
    )

    vector_a = [user_affinity.get(cuisine, 0.0) for cuisine in cuisines]
    vector_b = [candidate_affinity.get(cuisine, 0.0) for cuisine in cuisines]

    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = sum(a ** 2 for a in vector_a) ** 0.5
    magnitude_b = sum(b ** 2 for b in vector_b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    cosine = dot_product / (magnitude_a * magnitude_b)

    # Convert cosine similarity from [-1, 1] to [0, 1]
    return (cosine + 1) / 2


def jaccard_similarity(tags_a, tags_b):
    set_a = set(tags_a)
    set_b = set(tags_b)

    union = set_a | set_b
    intersection = set_a & set_b

    if not union:
        return 0.0

    return len(intersection) / len(union)


def score_users(user, candidates):
    results = []

    for candidate in candidates:

        # Never recommend the same user
        if candidate["user_id"] == user["user_id"]:
            continue

        # Hard filter: users must be in the same city
        if candidate["location"] != user["location"]:
            continue

        food_similarity = cosine_similarity(
            user["food_affinity"],
            candidate["food_affinity"]
        )

        interest_similarity = jaccard_similarity(
            user["interest_tags"],
            candidate["interest_tags"]
        )

        compatibility = (
            food_similarity * FOOD_AFFINITY_WEIGHT
            + interest_similarity * INTEREST_WEIGHT
        )

        results.append({
            **candidate,
            "compatibility_score": round(compatibility * 100, 1)
        })

    results.sort(
        key=lambda candidate: candidate["compatibility_score"],
        reverse=True
    )

    return results
