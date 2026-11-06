import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.synthetic_data import generate_data
from app.feature_store import (
    init_store,
    get_user,
    get_items,
    get_all_users
)
from app.recommendation import score_items
from app.matching import score_users
from app.card_rolling import build_cards
from app.feedback import process_feedback


# Initialize synthetic data once when the application starts
@asynccontextmanager
async def lifespan(app: FastAPI):
    data = generate_data()

    init_store(
        users=data["users"],
        items=data["items"],
        interactions=data["interactions"]
    )

    yield


app = FastAPI(
    title="Food Recommendation and Matching API",
    description="API for food recommendations, user matching and feed generation",
    version="1.0.0",
    lifespan=lifespan
)


# Request body for feedback
class FeedbackRequest(BaseModel):
    user_id: str
    item_id: str
    action: str


# Helper function to retrieve a user
def get_existing_user(user_id):
    user = get_user(user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail=f"User not found: {user_id}"
        )

    return user


# Health check
@app.get("/health")
def health_check():
    start_time = time.time()

    response = {
        "status": "ok"
    }

    response["response_time_ms"] = round(
        (time.time() - start_time) * 1000, 2
    )

    return response


# Get food recommendations
@app.get("/recommendations")
def get_recommendations(user_id: str):
    start_time = time.time()

    user = get_existing_user(user_id)

    recommendations = score_items(
        user=user,
        items=get_items()
    )

    response = {
        "user_id": user_id,
        "recommendations": recommendations[:10]
    }

    response["response_time_ms"] = round(
        (time.time() - start_time) * 1000, 2
    )

    return response


# Get compatible users
@app.get("/matches")
def get_matches(user_id: str):
    start_time = time.time()

    user = get_existing_user(user_id)

    matches = score_users(
        user=user,
        candidates=get_all_users()
    )

    response = {
        "user_id": user_id,
        "matches": matches[:10]
    }

    response["response_time_ms"] = round(
        (time.time() - start_time) * 1000, 2
    )

    return response


# Get combined food and person feed
@app.get("/cards")
def get_cards(user_id: str):
    start_time = time.time()

    user = get_existing_user(user_id)

    # Get top 10 food recommendations
    recommendations = score_items(
        user=user,
        items=get_items()
    )[:10]

    # Get top 10 compatible users
    matches = score_users(
        user=user,
        candidates=get_all_users()
    )[:10]

    # Combine both into one feed
    cards = build_cards(
        recommended_items=recommendations,
        matched_users=matches,
        recent_views=user["recent_views"]
    )

    response = {
        "user_id": user_id,
        "cards": cards
    }

    response["response_time_ms"] = round(
        (time.time() - start_time) * 1000, 2
    )

    return response


# Process user feedback
@app.post("/feedback")
def submit_feedback(request: FeedbackRequest):
    start_time = time.time()

    # Check user before processing feedback
    get_existing_user(request.user_id)

    try:
        updated_user = process_feedback(
            user_id=request.user_id,
            item_id=request.item_id,
            action=request.action
        )

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    response = {
        "user_id": request.user_id,
        "food_affinity": updated_user["food_affinity"],
        "recent_views": updated_user["recent_views"]
    }

    response["response_time_ms"] = round(
        (time.time() - start_time) * 1000, 2
    )

    return response