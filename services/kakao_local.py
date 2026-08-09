import os
from typing import Optional

import httpx

KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

COMPANION_KEYWORDS = {
    "애인": "데이트",
    "친구": "모임",
}

# https://developers.kakao.com/docs/latest/ko/local/dev-guide#search-by-keyword-category-group-code
RESTAURANT_CODE = "FD6"
CAFE_CODE = "CE7"


class KakaoLocalError(RuntimeError):
    pass


def _build_query(
    region: str,
    food_type: str,
    companion: Optional[str],
    headcount: int,
    drink: bool,
) -> str:
    parts = [region, food_type, "맛집"]
    if companion and companion in COMPANION_KEYWORDS:
        parts.append(COMPANION_KEYWORDS[companion])
    if headcount and headcount >= 5:
        parts.append("단체")
    if drink:
        parts.append("술집")
    return " ".join(parts)


async def search_restaurants(
    region: str,
    food_type: str,
    companion: Optional[str],
    headcount: int,
    drink: bool,
    size: int = 15,
) -> list[dict]:
    api_key = os.environ.get("KAKAO_REST_API_KEY")
    if not api_key:
        raise KakaoLocalError("KAKAO_REST_API_KEY가 설정되어 있지 않습니다.")

    query = _build_query(region, food_type, companion, headcount, drink)
    category_group_code = CAFE_CODE if food_type == "카페 디저트" else RESTAURANT_CODE

    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {
        "query": query,
        "size": size,
        "category_group_code": category_group_code,
        "sort": "accuracy",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(KEYWORD_SEARCH_URL, headers=headers, params=params)

    if resp.status_code != 200:
        raise KakaoLocalError(f"Kakao Local API 오류 ({resp.status_code}): {resp.text}")

    docs = resp.json().get("documents", [])

    results = []
    for doc in docs:
        results.append(
            {
                "id": doc.get("id"),
                "name": doc.get("place_name", ""),
                "category": doc.get("category_name", ""),
                "address": doc.get("road_address_name") or doc.get("address_name", ""),
                "phone": doc.get("phone") or None,
                "kakao_place_url": doc.get("place_url"),
            }
        )
    return results
