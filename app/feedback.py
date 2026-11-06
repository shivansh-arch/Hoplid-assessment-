from app.feature_store import update_user


def process_feedback(user_id, item_id, action):
    """Process feedback using the central feature store."""

    return update_user(
        user_id=user_id,
        item_id=item_id,
        action=action
    )