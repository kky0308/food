import asyncio
import os
from typing import Optional

import httpx

KEYWORD_SEARCH_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


async def _search_one(client: httpx.AsyncClient, api_key: str, query: str) -> Optional[dict]:
    headers = {"Authorization": f"KakaoAK {api_key}"}
    try:
        resp = await client.get(KEYWORD_SEARCH_URL, headers=headers, params={"query": query, "size": 1})
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    docs = resp.json().get("documents", [])
    if not docs:
        return None
    doc = docs[0]
    return {
        "kakao_place_url": doc.get("place_url"),
        "kakao_phone": doc.get("phone") or None,
    }


async def enrich_with_kakao_links(region: str, names: list[str]) -> list[Optional[dict]]:
    api_key = os.environ.get("KAKAO_REST_API_KEY")
    if not api_key:
        return [None] * len(names)

    async with httpx.AsyncClient(timeout=5.0) as client:
        tasks = [_search_one(client, api_key, f"{region} {name}") for name in names]
        return await asyncio.gather(*tasks)
