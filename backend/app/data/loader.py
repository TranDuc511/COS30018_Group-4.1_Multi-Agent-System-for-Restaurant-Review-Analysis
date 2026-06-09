import os
import json
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from app.data.matching import fuzzy_search

load_dotenv()

# Resolve dataset paths against the repository root so they work no matter the
# current working directory (project root, backend/, or anywhere else).
# loader.py lives at <repo>/backend/app/data/loader.py -> parents[3] == <repo>.
_REPO_ROOT = Path(__file__).resolve().parents[3]


def _resolve(path_str: str) -> str:
    path = Path(path_str)
    return str(path if path.is_absolute() else _REPO_ROOT / path)


BUSINESS_PATH = _resolve(
    os.getenv("YELP_BUSINESS_PATH", "backend/data/raw/yelp_academic_dataset_business.json")
)
REVIEW_PATH = _resolve(
    os.getenv("YELP_REVIEW_PATH", "backend/data/raw/yelp_academic_dataset_review.json")
)
MAX_REVIEWS = int(os.getenv("MAX_REVIEW_SAMPLE", 100))

# Cache — load once only
_businesses_cache = []


def _load_businesses() -> list[dict]:
    global _businesses_cache
    if _businesses_cache:
        return _businesses_cache
    print("Loading business dataset...")
    with open(BUSINESS_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            b = json.loads(line)
            _businesses_cache.append({
                "business_id":  b["business_id"],
                "name":         b["name"],
                "address":      b.get("address", ""),
                "city":         b.get("city", ""),
                "state":        b.get("state", ""),
                "review_count": b.get("review_count", 0),
            })
    print(f"Loaded {len(_businesses_cache)} businesses.")
    return _businesses_cache


def search_business(name: str, top_n: int = 3) -> list[dict]:
    """Load businesses from cache and fuzzy match against the entered name."""
    businesses = _load_businesses()
    return fuzzy_search(name, businesses, top_n)


def load_reviews(business_id: str) -> pd.DataFrame:
    """Load reviews for business_id, keeping the most recent MAX_REVIEWS."""
    rows = []
    with open(REVIEW_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("business_id") != business_id:
                continue
            rows.append({
                "review_id":   r["review_id"],
                "business_id": r["business_id"],
                "stars":       int(r["stars"]),
                "text":        r["text"],
                "date":        r["date"],
            })

    if not rows:
        print(f"No reviews found for business_id: {business_id}")
        return pd.DataFrame(columns=["review_id", "business_id", "stars", "text", "date"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date", ascending=False)

    total_found = len(df)
    if total_found <= MAX_REVIEWS:
        print(f"Business has {total_found} reviews — keeping all.")
    else:
        print(f"Business has {total_found} reviews — keeping the {MAX_REVIEWS} most recent.")
        df = df.head(MAX_REVIEWS)

    return df.reset_index(drop=True)
