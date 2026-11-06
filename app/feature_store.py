
# app/feature_store.py

import time


# Central feature store shared by all three engines.
user_features = {}

# Shared food catalogue.
items_catalog = []

# Fast item lookup index.
items_index = {}


# Feedback weights.
FEEDBACK_WEIGHTS = {
    "like": 1.0,
    "dislike": -1.5,
    "view": 0.1,
    "skip": -0.2
}


def init_store(users, items, interactions):
    """
    Initialize the feature store.

    1. Load users into the central dictionary.
    2. Build an item lookup index.
    3. Replay historical interactions through update_user().
    """

    user_features.clear()
    items_catalog.clear()
    items_index.clear()

    # Store the food catalogue.
    items_catalog.extend(items)

    # Build O(1) average-time lookup index.
    items_index.update({
        item["item_id"]: item
        for item in items
    })

    # Load users into the feature store.
    for user in users:
        user_features[user["user_id"]] = user

    # Replay historical interactions.
    for interaction in interactions:
        update_user(
            user_id=interaction["user_id"],
            item_id=interaction["item_id"],
            action=interaction["action"]
        )

    return user_features


def update_user(user_id, item_id, action):
    """
    Update a user's food affinity and recent views.

    Feedback weights:
        like:    +1.0
        dislike: -1.5
        view:    +0.1
        skip:    -0.2

    Food affinity is clamped between -3 and +3.
    Recent views retain the last 15 item IDs.
    """

    # Step 1: Find the user.
    user = user_features.get(user_id)

    if user is None:
        raise ValueError(f"User not found: {user_id}")

    # Step 2: Validate feedback action.
    if action not in FEEDBACK_WEIGHTS:
        raise ValueError(f"Invalid action: {action}")

    # Step 3: Find item using O(1) average lookup.
    item = items_index.get(item_id)

    if item is None:
        raise ValueError(f"Item not found: {item_id}")

    # Step 4: Identify the item's cuisine.
    cuisine = item["cuisine"]

    # Step 5: Get the feedback weight.
    weight = FEEDBACK_WEIGHTS[action]

    # Step 6: Calculate updated food affinity.
    current_score = user["food_affinity"].get(
        cuisine, 0.0
    )

    new_score = current_score + weight

    # Step 7: Clamp affinity between -3 and +3.
    user["food_affinity"][cuisine] = round(
        max(-3.0, min(3.0, new_score)),
        2
    )

    # Step 8: Update recent views using FIFO.
    recent_views = user["recent_views"]
    if item_id in recent_views:
        recent_views.remove(item_id)  # move to end instead of duplicating
    recent_views.append(item_id)
    if len(recent_views) > 15:
        del recent_views[:-15]

    # Step 9: Update timestamp.
    user["last_updated"] = time.time()

    return user


def get_user(user_id):
    """
    Retrieve a single user's feature record.
    Returns None if the user does not exist.
    """

    return user_features.get(user_id)


def get_all_users():
    """
    Retrieve all user feature records.
    Used by the matching engine.
    """

    return list(user_features.values())


def get_items():
    """
    Retrieve the shared food catalogue.
    Used by the recommendation engine.
    """

    return items_catalog
