const question = document.querySelector("#question");
const askForm = document.querySelector("#ask-form");
const askButton = document.querySelector("#ask-button");
const learnButton = document.querySelector("#learn-button");
const result = document.querySelector("#result");
const answerText = document.querySelector("#answer-text");
const citations = document.querySelector("#citations");
const answerStatus = document.querySelector("#answer-status");
const count = document.querySelector("#question-count");
const quizSection = document.querySelector("#quiz-section");
const quizForm = document.querySelector("#generated-quiz-form");
const quizStatus = document.querySelector("#quiz-status");
const generatedQuizResult = document.querySelector("#generated-quiz-result");

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

function renderCitations(items) {
  citations.innerHTML = items.map((citation, index) => `<div class="citation"><b>${String(index + 1).padStart(2, "0")}</b><div><strong>${escapeHtml(citation.problem_id || "Textbook passage")}</strong><span>${escapeHtml(citation.chapter || "Course material")} · Page ${escapeHtml(citation.page ?? "—")}</span></div></div>`).join("") || "<p>No citations returned.</p>";
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
    renderCitations(payload.citations);
  } catch (error) {
    answerStatus.textContent = "Request failed";
    answerText.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
  } finally {
    askButton.disabled = false;
    askButton.querySelector("span").textContent = "Ask Journey";
  }
});

function renderGeneratedQuiz(payload) {
  quizSection.classList.remove("hidden");
  generatedQuizResult.classList.remove("visible");
  generatedQuizResult.innerHTML = "";
  quizStatus.textContent = `${payload.quiz.length} questions`;
  quizForm.innerHTML = payload.quiz.map((item, questionIndex) => `<fieldset class="quiz-question"><legend><b>${questionIndex + 1}.</b> ${escapeHtml(item.question)}</legend>${item.choices.map((choice, choiceIndex) => `<label class="choice"><input type="radio" name="question-${questionIndex}" value="${choiceIndex}"><span>${escapeHtml(choice)}</span></label>`).join("")}</fieldset>`).join("") + '<button class="submit-quiz" type="submit">Check my answers <b>→</b></button>';
  quizForm.onsubmit = async (event) => {
    event.preventDefault();
    const choices = payload.quiz.map((_, index) => quizForm.querySelector(`input[name="question-${index}"]:checked`));
    if (choices.some((choice) => !choice)) {
      generatedQuizResult.textContent = "Choose an answer for every question first.";
      generatedQuizResult.classList.add("visible");
      return;
    }
    const button = quizForm.querySelector("button");
    button.disabled = true;
    button.firstChild.textContent = "Checking… ";
    try {
      const response = await fetch(`/learning-sessions/${payload.session_id}/submit`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ selected_choice_indexes: choices.map((choice) => Number(choice.value)) }) });
      const score = await response.json();
      if (!response.ok) throw new Error(score.detail || "Quiz evaluation failed.");
      generatedQuizResult.innerHTML = `<strong>${score.score_percent}% · ${escapeHtml(score.route)}</strong><span>${escapeHtml(score.next_action)}</span>`;
      generatedQuizResult.classList.add("visible");
      quizStatus.textContent = score.progress_message;
      if (score.progress_saved) await loadHistory(true);
    } catch (error) {
      generatedQuizResult.textContent = error.message;
      generatedQuizResult.classList.add("visible");
    } finally {
      button.disabled = false;
      button.firstChild.textContent = "Check my answers ";
    }
  };
}

learnButton.addEventListener("click", async () => {
  const text = question.value.trim();
  if (!text) return;
  learnButton.disabled = true;
  learnButton.querySelector("span").textContent = "Building quiz…";
  result.classList.remove("hidden");
  quizSection.classList.add("hidden");
  answerStatus.textContent = "Creating guided lesson";
  answerText.innerHTML = "<p class='loading'>Retrieving cited context and generating a quiz…</p>";
  citations.innerHTML = "";
  try {
    const response = await fetch("/learning-sessions", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: text, quiz_size: 3 }) });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || "The learning session could not be created.");
    answerStatus.textContent = "Cited lesson";
    answerText.innerHTML = `<p>${escapeHtml(payload.explanation).replaceAll("\n", "<br>")}</p>`;
    renderCitations(payload.citations);
    renderGeneratedQuiz(payload);
  } catch (error) {
    answerStatus.textContent = "Request failed";
    answerText.innerHTML = `<p class="error">${escapeHtml(error.message)}</p>`;
  } finally {
    learnButton.disabled = false;
    learnButton.querySelector("span").textContent = "Start guided quiz";
  }
});

let historyOffset = 0;
const historyPageSize = 20;
async function loadHistory(reset = false) {
  if (reset) historyOffset = 0;
  const panel = document.querySelector("#history-items");
  const status = document.querySelector("#history-status");
  const more = document.querySelector("#history-more");
  const refresh = document.querySelector("#history-refresh");
  more.disabled = true;
  refresh.disabled = true;
  status.textContent = "Loading history…";
  if (reset) panel.replaceChildren();
  try {
    const response = await fetch(`/progress-history?limit=${historyPageSize}&offset=${historyOffset}`);
    const entries = await response.json();
    if (!response.ok) throw new Error(entries.detail || "History could not be loaded.");
    for (const entry of entries) {
      const row = document.createElement("li");
      row.innerHTML = `<strong>${escapeHtml(entry.topic_label)} · ${entry.score}% · ${escapeHtml(entry.route)}</strong><p>${escapeHtml(entry.recommendation)}</p><time>${escapeHtml(new Date(entry.timestamp).toLocaleString())}</time>`;
      panel.append(row);
    }
    historyOffset += entries.length;
    status.textContent = historyOffset ? `${historyOffset} ${historyOffset === 1 ? "attempt" : "attempts"} shown. Times use your local timezone.` : "No completed quizzes saved yet.";
    more.hidden = entries.length < historyPageSize;
  } catch (error) {
    status.textContent = error.message;
    more.hidden = true;
  } finally {
    more.disabled = false;
    refresh.disabled = false;
  }
}
document.querySelector("#history-refresh").addEventListener("click", () => loadHistory(true));
document.querySelector("#history-more").addEventListener("click", () => loadHistory());
loadHistory(true);

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
