const state = { mode: "beginner", data: null, quiz: [], explanation: null };

const $ = (id) => document.getElementById(id);

// ---- mode toggle -----------------------------------------------------

document.querySelectorAll(".mode-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    state.mode = btn.dataset.mode;
  });
});

// ---- search / research -------------------------------------------------

$("search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const topic = $("topic").value.trim();
  if (!topic) return;

  $("search-error").textContent = "";
  $("search-btn").disabled = true;
  $("search-btn").textContent = "Searching…";
  $("results").hidden = true;

  try {
    const res = await fetch("/api/research", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topic, mode: state.mode }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Search failed.");
    const data = await res.json();
    state.data = data;
    state.quiz = [];
    state.explanation = null;
    renderResults(data);
    explainTopic(); // persona-styled summary/takeaways/vocab (this is what the mode actually changes)
  } catch (err) {
    $("search-error").textContent = err.message;
  } finally {
    $("search-btn").disabled = false;
    $("search-btn").textContent = "Search Wikipedia";
  }
});

function renderResults(data) {
  $("result-title").textContent = data.title;
  $("result-url").textContent = data.url;
  $("result-url").href = data.url;
  $("result-summary").textContent = data.summary; // raw Wikipedia summary, shown until the AI explanation loads
  $("result-takeaways").innerHTML = "";
  $("result-vocab").innerHTML = "";
  $("summary-mode-tag").textContent = "";

  const m = data.reading_metrics;
  $("metrics").innerHTML = `
    <div class="metric"><strong>${m.word_count}</strong>words</div>
    <div class="metric"><strong>${m.reading_time_minutes} min</strong>read time</div>
    <div class="metric"><strong>${m.complexity}</strong>complexity</div>
  `;

  $("related-topics").innerHTML = data.related_topics.length
    ? data.related_topics.map((t) => `<span class="chip">${escapeHtml(t)}</span>`).join("")
    : `<span class="hint">No related topics found.</span>`;

  $("quiz-form").innerHTML = "";
  $("quiz-score").hidden = true;
  $("quiz-error").textContent = "";
  $("results").hidden = false;
}

// ---- persona explanation (summary / takeaways / vocabulary) -------------

$("regenerate-btn").addEventListener("click", explainTopic);

async function explainTopic() {
  if (!state.data) return;
  $("explain-loading").hidden = false;
  $("regenerate-btn").disabled = true;

  try {
    const res = await fetch("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: state.data.title,
        article_text: state.data.content,
        mode: state.mode,
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Explanation failed.");
    const explanation = await res.json();
    state.explanation = explanation;
    renderExplanation(explanation, state.mode);
  } catch (err) {
    // Fall back to the raw Wikipedia summary already shown — not a hard failure.
    $("summary-mode-tag").textContent = "using Wikipedia summary (AI explanation unavailable)";
  } finally {
    $("explain-loading").hidden = true;
    $("regenerate-btn").disabled = false;
  }
}

function renderExplanation(explanation, mode) {
  $("result-summary").textContent = explanation.summary || "";
  $("summary-mode-tag").textContent = mode === "beginner" ? "Beginner (ELI5)" : "Academic";

  $("result-takeaways").innerHTML = (explanation.takeaways || [])
    .map((t) => `<li>${escapeHtml(t)}</li>`)
    .join("");

  $("result-vocab").innerHTML = (explanation.vocabulary || [])
    .map((v) => `<dt>${escapeHtml(v.term)}</dt><dd>${escapeHtml(v.definition)}</dd>`)
    .join("");
}

// ---- quiz ---------------------------------------------------------------

$("quiz-btn").addEventListener("click", async () => {
  if (!state.data) return;
  $("quiz-error").textContent = "";
  $("quiz-loading").hidden = false;
  $("quiz-btn").disabled = true;
  $("quiz-form").innerHTML = "";
  $("quiz-score").hidden = true;

  try {
    const res = await fetch("/api/quiz", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: state.data.title,
        article_text: state.data.content,
        mode: state.mode,
        num_questions: 5,
      }),
    });
    if (!res.ok) throw new Error((await res.json()).detail || "Quiz generation failed.");
    const { quiz } = await res.json();
    state.quiz = quiz;
    renderQuiz(quiz);
  } catch (err) {
    $("quiz-error").textContent = err.message;
  } finally {
    $("quiz-loading").hidden = true;
    $("quiz-btn").disabled = false;
  }
});

function renderQuiz(quiz) {
  const form = $("quiz-form");
  form.innerHTML = quiz
    .map(
      (q, qi) => `
    <div class="question" data-answer="${escapeHtml(q.answer)}">
      <p class="q-text">${qi + 1}. ${escapeHtml(q.question)}</p>
      ${q.options
        .map(
          (opt, oi) => `
        <label class="option">
          <input type="radio" name="q${qi}" value="${escapeHtml(opt)}" required>
          ${escapeHtml(opt)}
        </label>`
        )
        .join("")}
      <p class="explanation" hidden>${escapeHtml(q.explanation || "")}</p>
    </div>`
    )
    .join("") + `<button type="submit">Check answers</button>`;

  form.onsubmit = (e) => {
    e.preventDefault();
    gradeQuiz();
  };
}

function gradeQuiz() {
  let correct = 0;
  document.querySelectorAll(".question").forEach((qEl) => {
    const answer = qEl.dataset.answer;
    const selected = qEl.querySelector("input:checked");
    qEl.querySelectorAll(".option").forEach((optEl) => {
      const val = optEl.querySelector("input").value;
      if (val === answer) optEl.classList.add("correct");
      else if (selected && val === selected.value) optEl.classList.add("incorrect");
    });
    qEl.querySelector(".explanation").hidden = false;
    if (selected && selected.value === answer) correct++;
  });

  const total = state.quiz.length;
  const score = $("quiz-score");
  score.hidden = false;
  score.textContent = `Score: ${correct} / ${total}`;
}

// ---- export ---------------------------------------------------------------

$("export-btn").addEventListener("click", async () => {
  if (!state.data) return;
  $("export-btn").disabled = true;
  try {
    const res = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        topic: state.data.title,
        summary: (state.explanation && state.explanation.summary) || state.data.summary,
        reading_metrics: state.data.reading_metrics,
        related_topics: state.data.related_topics,
        takeaways: (state.explanation && state.explanation.takeaways) || [],
        vocabulary: (state.explanation && state.explanation.vocabulary) || [],
        quiz: state.quiz,
      }),
    });
    if (!res.ok) throw new Error("Export failed.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${state.data.title.replace(/[^a-zA-Z0-9]+/g, "_")}_study_deck.md`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    alert(err.message);
  } finally {
    $("export-btn").disabled = false;
  }
});

// ---- utils ---------------------------------------------------------------

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}
