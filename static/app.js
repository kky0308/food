const steps = ["1", "2", "3", "4", "5", "6", "result"];
let currentIndex = 0;

const state = {
  region: "",
  visit_date: "",
  visit_time: "19:00",
  companion: "",
  headcount: 2,
  food_type: "",
  drink: null, // true | false
};

const wizard = document.getElementById("wizard");
const progressEl = document.getElementById("progress");
const btnBack = document.getElementById("btn-back");
const btnNext = document.getElementById("btn-next");
const btnRestart = document.getElementById("btn-restart");

const regionInput = document.getElementById("region-input");
const regionChips = document.getElementById("region-chips");
const visitDateInput = document.getElementById("visit-date");
const visitTimeInput = document.getElementById("visit-time");
const companionOptions = document.getElementById("companion-options");
const foodOptions = document.getElementById("food-options");
const drinkOptions = document.getElementById("drink-options");
const headcountValue = document.getElementById("headcount-value");

function initProgressDots() {
  progressEl.innerHTML = "";
  for (let i = 0; i < steps.length - 1; i++) {
    const span = document.createElement("span");
    progressEl.appendChild(span);
  }
}
initProgressDots();

function updateProgress() {
  const dots = progressEl.querySelectorAll("span");
  dots.forEach((dot, i) => {
    dot.classList.toggle("done", i <= currentIndex);
  });
}

function showStep() {
  document.querySelectorAll(".step").forEach((sec) => {
    sec.classList.toggle("active", sec.dataset.step === steps[currentIndex]);
  });
  updateProgress();

  btnBack.classList.toggle("hidden", currentIndex === 0 || steps[currentIndex] === "result");
  btnNext.classList.toggle("hidden", steps[currentIndex] === "result");
  btnRestart.classList.toggle("hidden", steps[currentIndex] !== "result");

  btnNext.textContent = steps[currentIndex] === "6" ? "추천 받기" : "다음";
  btnNext.disabled = !isStepValid();
}

function isStepValid() {
  switch (steps[currentIndex]) {
    case "1":
      return state.region.trim().length > 0;
    case "2":
      return state.visit_date.length > 0 && state.visit_time.length > 0;
    case "3":
      return state.companion.length > 0;
    case "4":
      return state.headcount >= 1;
    case "5":
      return state.food_type.length > 0;
    case "6":
      return state.drink !== null;
    default:
      return true;
  }
}

regionInput.addEventListener("input", (e) => {
  state.region = e.target.value;
  [...regionChips.children].forEach((c) => c.classList.toggle("selected", c.dataset.value === state.region));
  btnNext.disabled = !isStepValid();
});

regionChips.addEventListener("click", (e) => {
  const btn = e.target.closest(".chip");
  if (!btn) return;
  state.region = btn.dataset.value;
  regionInput.value = state.region;
  [...regionChips.children].forEach((c) => c.classList.toggle("selected", c === btn));
  btnNext.disabled = !isStepValid();
});

const today = new Date();
visitDateInput.min = today.toISOString().slice(0, 10);
visitDateInput.value = today.toISOString().slice(0, 10);
state.visit_date = visitDateInput.value;
state.visit_time = visitTimeInput.value;

visitDateInput.addEventListener("change", (e) => {
  state.visit_date = e.target.value;
  btnNext.disabled = !isStepValid();
});
visitTimeInput.addEventListener("change", (e) => {
  state.visit_time = e.target.value;
  btnNext.disabled = !isStepValid();
});

function wireOptionCards(container, onSelect) {
  container.addEventListener("click", (e) => {
    const btn = e.target.closest(".option-card");
    if (!btn) return;
    [...container.children].forEach((c) => c.classList.toggle("selected", c === btn));
    onSelect(btn.dataset.value);
    btnNext.disabled = !isStepValid();
  });
}

wireOptionCards(companionOptions, (v) => (state.companion = v));
wireOptionCards(foodOptions, (v) => (state.food_type = v));
wireOptionCards(drinkOptions, (v) => (state.drink = v === "yes"));

document.getElementById("food-random").addEventListener("click", () => {
  const cards = [...foodOptions.children];
  const pick = cards[Math.floor(Math.random() * cards.length)];
  cards.forEach((c) => c.classList.toggle("selected", c === pick));
  state.food_type = pick.dataset.value;
  btnNext.disabled = !isStepValid();
});

document.getElementById("headcount-minus").addEventListener("click", () => {
  state.headcount = Math.max(1, state.headcount - 1);
  headcountValue.textContent = state.headcount;
});
document.getElementById("headcount-plus").addEventListener("click", () => {
  state.headcount = Math.min(50, state.headcount + 1);
  headcountValue.textContent = state.headcount;
});

btnBack.addEventListener("click", () => {
  if (currentIndex > 0) {
    currentIndex--;
    showStep();
  }
});

btnNext.addEventListener("click", async () => {
  if (!isStepValid()) return;
  if (steps[currentIndex] === "6") {
    await fetchRecommendations();
  }
  if (currentIndex < steps.length - 1) {
    currentIndex++;
    showStep();
  }
});

btnRestart.addEventListener("click", () => {
  currentIndex = 0;
  showStep();
});

async function fetchRecommendations() {
  const resultList = document.getElementById("result-list");
  const resultSummary = document.getElementById("result-summary");
  resultList.innerHTML = "";
  resultSummary.textContent = "추천 맛집을 찾는 중...";

  try {
    const res = await fetch("/api/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "추천을 가져오지 못했습니다.");
    }

    const data = await res.json();
    renderResults(data);
  } catch (err) {
    resultSummary.textContent = "";
    resultList.innerHTML = `<div class="error-state">${err.message}<br/>API 키가 설정되어 있는지 확인해주세요.</div>`;
  }
}

function renderResults(data) {
  const resultList = document.getElementById("result-list");
  const resultSummary = document.getElementById("result-summary");

  resultSummary.textContent = `${state.region} · ${state.food_type} · TOP ${data.count} (카카오맵 검색 결과)`;

  if (!data.results.length) {
    resultList.innerHTML = `<div class="empty-state">조건에 맞는 맛집을 찾지 못했어요. 지역이나 음식 종류를 바꿔보세요.</div>`;
    return;
  }

  resultList.innerHTML = data.results
    .slice(0, 5)
    .map((r, i) => {
      return `
        <div class="result-card">
          <div class="name"><span class="rank">${i + 1}</span>${r.name}</div>
          <div class="rating">${r.category || ""}</div>
          <div class="address">${r.address}</div>
          ${r.phone ? `<div class="address">${r.phone}</div>` : ""}
          <br/>
          ${r.kakao_place_url ? `<a href="${r.kakao_place_url}" target="_blank" rel="noopener">영업시간 · 휴무일 · 평점 카카오맵에서 확인 →</a>` : ""}
        </div>
      `;
    })
    .join("");
}

showStep();
