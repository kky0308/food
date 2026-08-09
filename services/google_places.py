import os
from datetime import datetime
from typing import Optional

import httpx

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"

FIELD_MASK = ",".join(
    [
        "places.id",
        "places.displayName",
        "places.formattedAddress",
        "places.rating",
        "places.userRatingCount",
        "places.priceLevel",
        "places.googleMapsUri",
        "places.regularOpeningHours",
        "places.types",
    ]
)

COMPANION_KEYWORDS = {
    "애인": "데이트",
    "친구": "모임",
}


class GooglePlacesError(RuntimeError):
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


def _weighted_rating(rating: float, user_rating_count: int, m: int = 10, c: float = 4.0) -> float:
    v = user_rating_count or 0
    if v == 0:
        return 0.0
    return (v / (v + m)) * rating + (m / (v + m)) * c


def _is_open_at(place: dict, visit_dt: Optional[datetime]) -> Optional[bool]:
    if visit_dt is None:
        return None
    hours = place.get("regularOpeningHours")
    if not hours or "periods" not in hours:
        return None

    google_day = (visit_dt.weekday() + 1) % 7  # Google: Sunday=0
    visit_minutes = visit_dt.hour * 60 + visit_dt.minute

    for period in hours["periods"]:
        open_info = period.get("open")
        close_info = period.get("close")
        if not open_info:
            continue
        open_day = open_info.get("day")
        open_minutes = open_info.get("hour", 0) * 60 + open_info.get("minute", 0)

        if not close_info:
            if open_day == google_day and visit_minutes >= open_minutes:
                return True
            continue

        close_day = close_info.get("day")
        close_minutes = close_info.get("hour", 0) * 60 + close_info.get("minute", 0)

        if open_day == close_day:
            if google_day == open_day and open_minutes <= visit_minutes < close_minutes:
                return True
        else:
            # overnight period (e.g. 22:00 ~ 02:00 next day)
            if google_day == open_day and visit_minutes >= open_minutes:
                return True
            if google_day == close_day and visit_minutes < close_minutes:
                return True

    return False


async def search_restaurants(
    region: str,
    food_type: str,
    companion: Optional[str],
    headcount: int,
    drink: bool,
    visit_dt: Optional[datetime] = None,
    max_results: int = 20,
) -> list[dict]:
    api_key = os.environ.get("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise GooglePlacesError("GOOGLE_PLACES_API_KEY가 설정되어 있지 않습니다.")

    query = _build_query(region, food_type, companion, headcount, drink)

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": FIELD_MASK,
    }
    body = {
        "textQuery": query,
        "languageCode": "ko",
        "regionCode": "KR",
        "maxResultCount": max_results,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(PLACES_SEARCH_URL, headers=headers, json=body)

    if resp.status_code != 200:
        raise GooglePlacesError(f"Google Places API 오류 ({resp.status_code}): {resp.text}")

    data = resp.json()
    places = data.get("places", [])

    results = []
    for place in places:
        rating = place.get("rating")
        user_rating_count = place.get("userRatingCount", 0)
        if rating is None:
            continue
        results.append(
            {
                "id": place.get("id"),
                "name": place.get("displayName", {}).get("text", ""),
                "address": place.get("formattedAddress", ""),
                "rating": rating,
                "user_rating_count": user_rating_count,
                "weighted_rating": round(_weighted_rating(rating, user_rating_count), 3),
                "price_level": place.get("priceLevel"),
                "google_maps_uri": place.get("googleMapsUri"),
                "types": place.get("types", []),
                "is_open_at_visit": _is_open_at(place, visit_dt),
            }
        )

    def sort_key(item: dict):
        # open (or unknown) places first, then by weighted rating desc
        open_bucket = 0 if item["is_open_at_visit"] is not False else 1
        return (open_bucket, -item["weighted_rating"])

    results.sort(key=sort_key)
    return results
