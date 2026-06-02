import os
import json
import pandas as pd
from dotenv import load_dotenv
from app.data.matching import fuzzy_search

load_dotenv()

BUSINESS_PATH = os.getenv("YELP_BUSINESS_PATH", "backend/data/raw/yelp_academic_dataset_business.json")
REVIEW_PATH   = os.getenv("YELP_REVIEW_PATH",   "backend/data/raw/yelp_academic_dataset_review.json")
MAX_REVIEWS   = int(os.getenv("MAX_REVIEW_SAMPLE", 100))

# Cache — load 1 lần duy nhất
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
    """Load businesses từ cache và fuzzy match với tên nhập vào."""
    businesses = _load_businesses()
    return fuzzy_search(name, businesses, top_n)


def load_reviews(business_id: str) -> pd.DataFrame:
    """Load reviews của business_id, lấy MAX_REVIEWS gần nhất."""
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
        print(f"Không tìm thấy review nào cho business_id: {business_id}")
        return pd.DataFrame(columns=["review_id", "business_id", "stars", "text", "date"])

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date", ascending=False)

    total_found = len(df)
    if total_found <= MAX_REVIEWS:
        print(f"Business có {total_found} reviews — lấy hết.")
    else:
        print(f"Business có {total_found} reviews — lấy {MAX_REVIEWS} mới nhất.")
        df = df.head(MAX_REVIEWS)

    return df.reset_index(drop=True)