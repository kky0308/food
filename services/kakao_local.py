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


def _extra_keywords(companion: Optional[str], headcount: int, drink: bool) -> list[str]:
    extras = []
    if companion and companion in COMPANION_KEYWORDS:
        extras.append(COMPANION_KEYWORDS[companion])
    if headcount and headcount >= 5:
        extras.append("단체")
    if drink:
        extras.append("술집")
    return extras


def _build_attempts(
    region: str,
    food_type: str,
    companion: Optional[str],
    headcount: int,
    drink: bool,
    category_group_code: str,
) -> list[dict]:
    base_query = f"{region} {food_type}"
    extras = _extra_keywords(companion, headcount, drink)

    attempts = []
    if extras:
        # 가장 구체적인 조건부터 시도하고, 결과가 없으면 점점 조건을 완화한다.
        attempts.append({"query": f"{base_query} {' '.join(extras)}", "category_group_code": category_group_code})
    attempts.append({"query": base_query, "category_group_code": category_group_code})
    attempts.append({"query": base_query, "category_group_code": None})
    return attempts


async def _search_once(client: httpx.AsyncClient, api_key: str, query: str, category_group_code: Optional[str], size: int) -> list[dict]:
    headers = {"Authorization": f"KakaoAK {api_key}"}
    params = {"query": query, "size": size, "sort": "accuracy"}
    if category_group_code:
        params["category_group_code"] = category_group_code

    resp = await client.get(KEYWORD_SEARCH_URL, headers=headers, params=params)
    if resp.status_code != 200:
        raise KakaoLocalError(f"Kakao Local API 오류 ({resp.status_code}): {resp.text}")

    return resp.json().get("documents", [])


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

    category_group_code = CAFE_CODE if food_type == "카페 디저트" else RESTAURANT_CODE
    attempts = _build_attempts(region, food_type, companion, headcount, drink, category_group_code)

    docs: list[dict] = []
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in attempts:
            docs = await _search_once(client, api_key, attempt["query"], attempt["category_group_code"], size)
            if docs:
                break

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
