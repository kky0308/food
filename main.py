from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from services.kakao_local import KakaoLocalError, search_restaurants

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
    try:
        results = await search_restaurants(
            region=req.region,
            food_type=req.food_type,
            companion=req.companion,
            headcount=req.headcount,
            drink=req.drink,
        )
    except KakaoLocalError as e:
        raise HTTPException(status_code=502, detail=str(e))

    top5 = results[:5]
    return {"query": req.model_dump(), "count": len(top5), "results": top5}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
