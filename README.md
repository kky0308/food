# 오늘 뭐 먹지? - 맛집 추천

지역, 방문 날짜/시간, 동반자, 인원수, 음식 종류, 음주 여부를 단계별로 선택하면
Google 평점(리뷰 수 가중치 적용) 기준으로 맛집을 추천해주는 웹앱입니다.
결과에는 참고용 카카오맵 링크도 함께 제공됩니다. (카카오 공식 API는 별점을 제공하지 않아
평점 자체는 Google 평점만 사용합니다.)

## 기술 스택

- Backend: FastAPI (Python)
- Frontend: Vanilla HTML/CSS/JS (단계별 마법사 UI)
- 외부 API: Google Places API (New) - Text Search, Kakao Local API (지도 링크용)

## 로컬 실행

```bash
pip install -r requirements.txt
cp .env.example .env  # 발급받은 API 키 입력
uvicorn main:app --reload
```

`http://localhost:8000` 접속.

### API 키 발급

- **Google Places API**: Google Cloud Console에서 프로젝트 생성 → Places API (New) 활성화 →
  사용자 인증 정보에서 API 키 발급. (`GOOGLE_PLACES_API_KEY`)
- **Kakao REST API**: developers.kakao.com 가입 → 애플리케이션 추가 → REST API 키 확인.
  (`KAKAO_REST_API_KEY`, 무료, 카드 등록 불필요)

## Docker

```bash
docker build -t food-recommend .
docker run -p 8000:8000 --env-file .env food-recommend
```

## API

`POST /api/recommend`

```json
{
  "region": "강남역",
  "visit_date": "2026-08-09",
  "visit_time": "19:00",
  "companion": "친구",
  "headcount": 4,
  "food_type": "이자카야",
  "drink": true
}
```
