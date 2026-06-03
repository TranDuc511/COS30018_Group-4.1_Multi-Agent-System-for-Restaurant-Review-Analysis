import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.data.loader import search_business, load_reviews
from app.data.preprocessor import preprocess

# ================================================
# Test 1 - Fuzzy Search
# ================================================
print("=" * 50)
print("FUZZY SEARCH")
print("=" * 50)

business_name = input("Nhập tên restaurant: ")
results = search_business(business_name)

if not results:
    print("Không tìm thấy business nào phù hợp.")
    sys.exit(1)

if results[0]["score"] == 100:
    print(f"\nTìm thấy {len(results)} chi nhánh khớp chính xác:\n")
else:
    print(f"\nKhông tìm thấy khớp chính xác. Top {len(results)} gần nhất:\n")

for i, r in enumerate(results):
    print(f"{i+1}. {r['name']}")
    print(f"   Address  : {r['address']}, {r['city']}, {r['state']}")
    print(f"   Reviews  : {r['review_count']}")
    print(f"   Score    : {r['score']}")
    print(f"   ID       : {r['business_id']}")
    print()

# User chọn chi nhánh
while True:
    try:
        choice = int(input(f"Chọn chi nhánh (1-{len(results)}): "))
        if 1 <= choice <= len(results):
            break
        print(f"Vui lòng nhập số từ 1 đến {len(results)}.")
    except ValueError:
        print("Vui lòng nhập số.")

selected = results[choice - 1]
business_id = selected["business_id"]
print(f"\n>> Đã chọn: {selected['name']} - {selected['address']}, {selected['city']}\n")

# ================================================
# Test 2 - Load Reviews
# ================================================
print("=" * 50)
print("LOAD REVIEWS")
print("=" * 50)

df_raw = load_reviews(business_id)

if df_raw.empty:
    print("Không có review nào. Kết thúc.")
    sys.exit(1)

print(f"Tổng reviews : {len(df_raw)}")
print(f"Từ           : {df_raw['date'].min().date()} đến {df_raw['date'].max().date()}")
print(f"Avg stars    : {df_raw['stars'].mean():.1f} ★")

# ================================================
# Test 3 - Preprocess
# ================================================
print()
print("=" * 50)
print("PREPROCESS")
print("=" * 50)

df_clean = preprocess(df_raw)
print(f"Reviews sau clean : {len(df_clean)}")
print()
print("Schema:")
print(df_clean.dtypes)

# Sample reviews
print()
print("Sample 3 reviews:")
print("-" * 50)
for _, row in df_clean.head(3).iterrows():
    print(f"ID    : {row['review_id']}")
    print(f"Stars : {'★' * row['stars']}{'☆' * (5 - row['stars'])} ({row['stars']})")
    print(f"Date  : {row['date'].date()}")
    print(f"Text  : {row['text'][:120]}...")
    print("-" * 50)

# ================================================
# Lưu output ra processed/
# ================================================
OUTPUT_PATH = "backend/data/processed/sample_reviews.json"
os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
df_clean.to_json(OUTPUT_PATH, orient="records", indent=2, force_ascii=False, date_format="iso")
print(f"\nĐã lưu ra: {OUTPUT_PATH}")

# File chỉ có text — cho LLM xử lý
OUTPUT_TEXT = "backend/data/processed/sample_reviews_text.json"
df_text = df_clean[["text"]].copy()
df_text.to_json(OUTPUT_TEXT, orient="records", indent=2, force_ascii=False)
print(f"Đã lưu text only : {OUTPUT_TEXT}")