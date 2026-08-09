from datetime import datetime
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from services.google_places import GooglePlacesError, search_restaurants
from services.kakao_local import enrich_with_kakao_links

load_dotenv()

app = FastAPI(title="맛집 추천")


class RecommendRequest(BaseModel):
    region: str = Field(..., min_length=1)
    visit_date: Optional[str] = None  # YYYY-MM-DD
    visit_time: Optional[str] = None  # HH:MM
    companion: Optional[str] = None  # "애인" | "친구"
    headcount: int = Field(default=2, ge=1, le=50)
    food_type: str = Field(..., min_length=1)
    drink: bool = False


@app.post("/api/recommend")
async def recommend(req: RecommendRequest):
    visit_dt = None
    if req.visit_date and req.visit_time:
        try:
            visit_dt = datetime.strptime(f"{req.visit_date} {req.visit_time}", "%Y-%m-%d %H:%M")
        except ValueError:
            visit_dt = None

    try:
        results = await search_restaurants(
            region=req.region,
            food_type=req.food_type,
            companion=req.companion,
            headcount=req.headcount,
            drink=req.drink,
            visit_dt=visit_dt,
        )
    except GooglePlacesError as e:
        raise HTTPException(status_code=502, detail=str(e))

    top_results = results[:10]
    kakao_links = await enrich_with_kakao_links(req.region, [r["name"] for r in top_results])
    for r, kakao in zip(top_results, kakao_links):
        r["kakao_place_url"] = kakao["kakao_place_url"] if kakao else None
        r["kakao_phone"] = kakao["kakao_phone"] if kakao else None

    return {"query": req.model_dump(), "count": len(results), "results": results}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
