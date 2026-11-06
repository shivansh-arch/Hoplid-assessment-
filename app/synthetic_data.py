
# app/synthetic_data.py

import random
import time

CUISINES = [
    "Indian", "Chinese", "Italian",
    "Mexican", "Japanese", "Thai", "American"
]

FOOD_NAMES = [
    ("Biryani", "Indian"),
    ("Pizza", "Italian"),
    ("Butter Chicken", "Indian"),
    ("Noodles", "Chinese"),
    ("Sushi", "Japanese"),
    ("Tacos", "Mexican"),
    ("Pasta", "Italian"),
    ("Ramen", "Japanese"),
    ("Paneer Tikka", "Indian"),
    ("Burger", "American")
]

INTERESTS = [
    "foodie", "fitness", "travel",
    "technology", "cooking",
    "nightlife", "healthy_food", "budget"
]


def generate_data():
    """Generate all synthetic application data."""

    rng = random.Random(42)

    # Generate 20 restaurants.
    restaurants = []

    for i in range(20):
        restaurants.append({
            "restaurant_id": f"R{i+1}",
            "name": f"Restaurant {i+1}",
            "location": rng.choice(
                ["Delhi", "Jaipur", "Alwar"]
            ),
            "price_level": rng.choice(
                ["low", "medium", "high"]
            ),
            "rating": round(
                rng.uniform(3.0, 5.0), 1
            ),
            "popularity": rng.randint(10, 100)
        })

    # Generate 50 food items.
    items = []

    for i in range(50):

        name, cuisine = FOOD_NAMES[i % len(FOOD_NAMES)]

        restaurant = rng.choice(restaurants)

        items.append({
            "item_id": f"F{i+1}",
            "name": name,
            "cuisine": cuisine,
            "restaurant_id": restaurant["restaurant_id"],
            "price_level": restaurant["price_level"],
            "rating": round(
                rng.uniform(3.0, 5.0), 1
            ),
            "popularity": rng.randint(10, 100),
            "location": restaurant["location"]
        })

    # Generate 100 users.
    users = []

    for i in range(100):

        food_affinity = {
            cuisine: round(
                rng.uniform(-2.0, 2.0), 2
            )
            for cuisine in CUISINES
        }

        users.append({
            "user_id": f"U{i+1}",
            "food_affinity": food_affinity,
            "price_pref": rng.choice(
                ["low", "medium", "high"]
            ),
            "location": rng.choice(
                ["Delhi", "Jaipur", "Alwar"]
            ),
            "interest_tags": rng.sample(
                INTERESTS,
                k=rng.randint(2, 5)
            ),
            "recent_views": [],
            "last_updated": time.time()
        })

    # Generate historical interactions.
    interactions = []

    for _ in range(300):

        user = rng.choice(users)
        item = rng.choice(items)

        interactions.append({
            "user_id": user["user_id"],
            "item_id": item["item_id"],
            "action": rng.choice([
                "like", "dislike", "view", "skip"
            ])
        })

    return {
        "users": users,
        "items": items,
        "restaurants": restaurants,
        "interactions": interactions
    }


if __name__ == "__main__":

    data = generate_data()

    print("Users:", len(data["users"]))
    print("Food items:", len(data["items"]))
    print("Restaurants:", len(data["restaurants"]))
    print("Interactions:", len(data["interactions"]))
