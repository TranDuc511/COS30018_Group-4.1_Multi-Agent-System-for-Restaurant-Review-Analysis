from fuzzywuzzy import process


def fuzzy_search(name: str, businesses: list[dict], top_n: int = 3) -> list[dict]:
    """Fuzzy match tên business, trả về top_n candidates không trùng business_id.
    Ưu tiên score cao nhất, nếu bằng nhau thì ưu tiên nhiều review nhất.
    """
    names = [b["name"] for b in businesses]
    matches = process.extract(name, names, limit=top_n * 20)

    seen = {}
    for match_name, score in matches:
        for idx, n in enumerate(names):
            if n == match_name:
                biz = businesses[idx]
                bid = biz["business_id"]
                if bid not in seen:
                    seen[bid] = {**biz, "score": score}

        if len(seen) >= top_n * 5:
            break

    results = sorted(
        seen.values(),
        key=lambda x: (x["score"], x["review_count"]),
        reverse=True
    )[:top_n]

    return results