import random


FEED_LIMIT = 10
TOP_N = 10
EXPLORATION_RATE = 0.10

def normalize_food_scores(items):
    if not items:
        return {}
    scores = [i["score"] for i in items]
    lo, hi = min(scores), max(scores)
    span = hi - lo if hi != lo else 1
    return {i["item_id"]: (i["score"] - lo) / span * 100 for i in items}

def build_cards(recommended_items, matched_users, recent_views):
    recent_views = set(recent_views or [])

    # Compute normalization ONCE, outside the loop, using the full list
    food_score_map = normalize_food_scores(recommended_items)

    cards = []
    exploration_candidates = []

    # 1. Prepare food cards
    for index, item in enumerate(recommended_items):
        item_id = item["item_id"]
        if item_id in recent_views:
            continue

        card = {
            **item,
            "card_type": "food",
            "id": item_id,
            "name": item["name"],
            "score": item["score"],
            "_rank_score": food_score_map[item_id]   # ← lookup, not a function call
        }

        if index < TOP_N:
            cards.append(card)
        else:
            exploration_candidates.append(card)

    # ... rest of the file unchanged

    # 2. Prepare person cards
    for index, person in enumerate(matched_users):

        person_id = person["user_id"]

        if person_id in recent_views:
            continue

        card = {
            **person,
            "card_type": "person",
            "id": person_id,
            "name": person.get("name", person_id),
            "score": person["compatibility_score"],
            "_rank_score": person["compatibility_score"]
        }

        if index < TOP_N:
            cards.append(card)
        else:
            exploration_candidates.append(card)

    # 3. Merge and sort using the internal comparable score
    cards.sort(
        key=lambda card: card["_rank_score"],
        reverse=True
    )

    # 4. Exploration: occasionally inject one lower-ranked card
    if (
        exploration_candidates
        and random.random() < EXPLORATION_RATE
    ):
        # Select one lower-ranked candidate
        candidate = random.choice(exploration_candidates)

        # Insert it within the feed instead of always putting it last
        insert_position = random.randint(0, min(4, len(cards)))
        cards.insert(insert_position, candidate)

    # 5. Apply cuisine diversity
    diverse_cards = []
    remaining_cards = cards.copy()

    while remaining_cards:

        if len(diverse_cards) >= 2:

            last_two = diverse_cards[-2:]

            # Check whether the last two cards are food
            # cards from the same cuisine
            if (
                last_two[0]["card_type"] == "food"
                and last_two[1]["card_type"] == "food"
                and last_two[0].get("cuisine")
                == last_two[1].get("cuisine")
            ):
                last_cuisine = last_two[0]["cuisine"]

                # Find the next card that breaks the pattern
                alternative_index = next(
                    (
                        i for i, card in enumerate(remaining_cards)
                        if (
                            card["card_type"] != "food"
                            or card.get("cuisine") != last_cuisine
                        )
                    ),
                    None
                )

                if alternative_index is not None:
                    diverse_cards.append(
                        remaining_cards.pop(alternative_index)
                    )
                    continue

        diverse_cards.append(remaining_cards.pop(0))

    # 6. Return final feed, removing internal ranking field
    final_cards = []

    for card in diverse_cards[:FEED_LIMIT]:
        card.pop("_rank_score", None)
        final_cards.append(card)

    return final_cards