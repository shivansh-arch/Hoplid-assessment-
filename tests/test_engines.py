
import pytest

from app.synthetic_data import generate_data
from app.feature_store import (
    init_store,
    get_user,
    get_all_users,
    get_items,
    update_user
)
from app.recommendation import score_items
from app.matching import score_users
from app.card_rolling import build_cards


@pytest.fixture
def setup_store():
    """
    Generate synthetic data and initialize the shared feature store.
    Each test gets a fresh store.
    """
    data = generate_data()

    init_store(
        users=data["users"],
        items=data["items"],
        interactions=data["interactions"]
    )

    return data


def get_user_with_matches():
    """
    Find a user who has at least one other user in the same city.
    """
    users = get_all_users()

    for user in users:
        candidates = [
            candidate
            for candidate in users
            if (
                candidate["user_id"] != user["user_id"]
                and candidate["location"] == user["location"]
            )
        ]

        if candidates:
            return user

    return None


def test_recommendation_filters_recent_views(setup_store):
    """
    Recently viewed food items should not appear in recommendations.
    """
    user = get_all_users()[0]
    items = get_items()

    # Pick an item that is not already recently viewed
    item = next(
        item for item in items
        if item["item_id"] not in user["recent_views"]
    )

    item_id = item["item_id"]

    # Manually add it to recent views
    user["recent_views"].append(item_id)

    recommendations = score_items(user, items)

    recommended_ids = {
        result["item_id"] for result in recommendations
    }

    assert item_id not in recommended_ids


def test_matching_same_location_only(setup_store):
    """
    Matches must belong to the same city and exclude the input user.
    """
    user = get_user_with_matches()

    assert user is not None, "No user with same-city candidates found"

    matches = score_users(
        user=user,
        candidates=get_all_users()
    )

    for match in matches:
        assert match["location"] == user["location"]
        assert match["user_id"] != user["user_id"]


def test_card_rolling_returns_mixed_types(setup_store):
    """
    The final feed should contain both food and person cards.
    """
    user = get_user_with_matches()

    if user is None:
        pytest.skip("No user has same-city matching candidates")

    recommendations = score_items(
        user=user,
        items=get_items()
    )[:10]

    matches = score_users(
        user=user,
        candidates=get_all_users()
    )[:10]

    if not recommendations:
        pytest.skip("No food recommendations available")

    if not matches:
        pytest.skip("No same-city matches available")

    cards = build_cards(
        recommended_items=recommendations,
        matched_users=matches,
        recent_views=user["recent_views"]
    )

    card_types = {
        card["card_type"] for card in cards
    }

    assert "food" in card_types
    assert "person" in card_types


def test_feedback_changes_recommendation(setup_store):
    """
    Liking an item should increase the score of items
    belonging to the same cuisine.
    """
    user = get_all_users()[0]
    items = get_items()

    # Find an item from a cuisine with low affinity
    eligible_items = [
        item for item in items
        if item["item_id"] not in user["recent_views"]
    ]

    assert eligible_items, "No eligible food items found"

    item = min(
        eligible_items,
        key=lambda item: user["food_affinity"].get(
            item["cuisine"], 0.0
        )
    )

    cuisine = item["cuisine"]
    item_id = item["item_id"]

    current_affinity = user["food_affinity"].get(cuisine, 0.0)

    # Avoid testing a saturated affinity score
    if current_affinity >= 3.0:
        pytest.skip("Selected cuisine already has maximum affinity")

    # Get recommendation score before feedback
    before = score_items(user, items)

    before_scores = {
        result["item_id"]: result["score"]
        for result in before
    }

    assert item_id in before_scores

    old_score = before_scores[item_id]

    # Like the selected food item
    update_user(
        user_id=user["user_id"],
        item_id=item_id,
        action="like"
    )

    # Remove the item from recent views so we can measure
    # the preference-based score change independently.
    user["recent_views"].remove(item_id)

    # Get recommendation score after feedback
    after = score_items(user, items)

    after_scores = {
        result["item_id"]: result["score"]
        for result in after
    }

    new_score = after_scores[item_id]

    assert new_score > old_score
