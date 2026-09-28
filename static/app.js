const question = document.querySelector("#question");
const askForm = document.querySelector("#ask-form");
const askButton = document.querySelector("#ask-button");
const result = document.querySelector("#result");
const answerText = document.querySelector("#answer-text");
const citations = document.querySelector("#citations");
const answerStatus = document.querySelector("#answer-status");
const count = document.querySelector("#question-count");

function updateCount() { count.textContent = `${question.value.length} / 1000`; }
updateCount();
question.addEventListener("input", updateCount);

document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => { question.value = button.dataset.question; updateCount(); question.focus(); });
});

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value ?? "";
  return element.innerHTML;
}

askForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = question.value.trim();
  if (!text) return;
  askButton.disabled = true;
  askButton.querySelector("span").textContent = "Retrieving…";
  result.classList.remove("hidden");
  answerStatus.textContent = "Searching textbook";
  answerText.innerHTML = "<p class='loading'>Building a grounded answer from the local retrieval pipeline…</p>";
  citations.innerHTML = "";
  try {
    const response = await fetch("/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: text }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The request could not be completed.");
    answerStatus.textContent = "Cited response";
    answerText.innerHTML = `<p>${escapeHtml(payload.answer).replaceAll("\n", "<br>")}</p>`;
    citations.innerHTML = payload.citations.map((citation, index) => `<div class="citation"><b>${String(index + 1).padStart(2, "0")}</b><div><strong>${escapeHtml(citation.problem_id || "Textbook passage")}</strong><span>${escapeHtml(citation.chapter || "Course material")} · Page ${escapeHtml(citation.page ?? "—")}</span></div></div>`).join("") || "<p>No citations returned.</p>";
  } catch (error) {
    answerStatus.textContent = "Request failed";
    answerText.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
  } finally {
    askButton.disabled = false;
    askButton.querySelector("span").textContent = "Ask Journey";
  }
});

document.querySelector("#quiz-button").addEventListener("click", async () => {
  const button = document.querySelector("#quiz-button");
  const panel = document.querySelector("#quiz-result");
  button.disabled = true;
  button.firstChild.textContent = "Evaluating… ";
  try {
    const sessionResponse = await fetch("/local-quiz-sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ answer_key: [1, 0, 2] }) });
    const session = await sessionResponse.json();
    const submitResponse = await fetch(`/local-quiz-sessions/${session.session_id}/submit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ selected_choice_indexes: [1, 0, 2] }) });
    const score = await submitResponse.json();
    panel.innerHTML = `<strong>${score.score_percent}% · ${escapeHtml(score.route)}</strong><span>${escapeHtml(score.next_action)}</span>`;
    panel.classList.add("visible");
  } catch (error) {
    panel.textContent = "Quiz demo could not be completed.";
    panel.classList.add("visible");
  } finally {
    button.disabled = false;
    button.firstChild.textContent = "Run quiz demo ";
  }
});
