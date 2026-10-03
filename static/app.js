// HalluciGuard Dashboard Client Script

let modelChart = null;
let promptChart = null;
let benchmarkQuestions = [];
let benchmarkResults = [];

document.addEventListener("DOMContentLoaded", () => {
  initNavigation();
  loadDashboardStats();
  loadBenchmarkData();
  loadResultsData();
});

// 1. Navigation Controller
function initNavigation() {
  const navButtons = document.querySelectorAll(".nav-item");
  navButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetSection = btn.dataset.section;
      switchNav(targetSection);
    });
  });
}

function switchNav(sectionId) {
  document.querySelectorAll(".nav-item").forEach(b => {
    b.classList.toggle("active", b.dataset.section === sectionId);
  });
  
  document.querySelectorAll(".content-section").forEach(sec => {
    sec.classList.toggle("active", sec.id === `section-${sectionId}`);
  });

  if (sectionId === "dashboard") {
    loadDashboardStats();
  }
}

// 2. Load Dashboard Statistics & Charts
async function loadDashboardStats() {
  try {
    const res = await fetch("/api/statistics");
    if (!res.ok) throw new Error("Failed to load statistics");
    const data = await res.json();

    // Populate Top Metrics
    document.getElementById("stat-total-combinations").textContent = data.total_combinations;
    document.getElementById("stat-successful-evaluations").textContent = data.successful_evaluations;
    document.getElementById("stat-api-failures").textContent = data.api_failures;
    document.getElementById("stat-trap-questions").textContent = data.trap_questions;

    // Transparency banner
    document.getElementById("transparency-text").textContent = data.transparency_note;

    // Classification boxes
    const c = data.classifications;
    document.getElementById("class-correct").textContent = c.correct;
    document.getElementById("class-hallucinated").textContent = c.hallucinated;
    document.getElementById("class-partial").textContent = c.partial_hallucination;
    document.getElementById("class-uncertain").textContent = c.uncertain;
    document.getElementById("class-error").textContent = c.api_errors;

    // Sample sizes
    const hr = data.hallucination_rates;
    document.getElementById("sample-models").textContent = `OpenAI (n=${hr.openai_overall.sample_size}) vs Gemini (n=${hr.gemini_overall.sample_size})`;
    document.getElementById("sample-prompts").textContent = `V1 (n=${hr.v1_overall.sample_size}) | V2 (n=${hr.v2_overall.sample_size}) | V3 (n=${hr.v3_overall.sample_size})`;

    renderModelChart(hr);
    renderPromptChart(hr);
  } catch (err) {
    console.error("Dashboard stats error:", err);
  }
}

function renderModelChart(hr) {
  const ctx = document.getElementById("chart-models");
  if (!ctx) return;

  if (modelChart) {
    modelChart.destroy();
  }

  modelChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["OpenAI (gpt-6-luna)", "Gemini (gemini-3.8-flash)"],
      datasets: [{
        label: "Hallucination Rate (%)",
        data: [hr.openai_overall.rate, hr.gemini_overall.rate],
        backgroundColor: [
          "rgba(16, 163, 127, 0.6)",
          "rgba(66, 133, 244, 0.6)"
        ],
        borderColor: [
          "#10a37f",
          "#4285f4"
        ],
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Hallucination Rate: ${ctx.parsed.y}%`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 100,
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#94a3b8",
            callback: (v) => `${v}%`
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: "#e2e8f0" }
        }
      }
    }
  });
}

function renderPromptChart(hr) {
  const ctx = document.getElementById("chart-prompts");
  if (!ctx) return;

  if (promptChart) {
    promptChart.destroy();
  }

  promptChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["V1 (Basic)", "V2 (Fact-Check)", "V3 (Defensive)"],
      datasets: [{
        label: "Hallucination Rate (%)",
        data: [hr.v1_overall.rate, hr.v2_overall.rate, hr.v3_overall.rate],
        backgroundColor: [
          "rgba(148, 163, 184, 0.6)",
          "rgba(6, 182, 212, 0.6)",
          "rgba(139, 92, 246, 0.6)"
        ],
        borderColor: [
          "#94a3b8",
          "#06b6d4",
          "#8b5cf6"
        ],
        borderWidth: 1.5,
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Hallucination Rate: ${ctx.parsed.y}%`
          }
        }
      },
      scales: {
        y: {
          beginAtZero: true,
          max: 60,
          grid: { color: "rgba(255, 255, 255, 0.05)" },
          ticks: {
            color: "#94a3b8",
            callback: (v) => `${v}%`
          }
        },
        x: {
          grid: { display: false },
          ticks: { color: "#e2e8f0" }
        }
      }
    }
  });
}

// 3. Live Stress Test
function loadPreset(type) {
  const input = document.getElementById("live-question-input");
  if (type === "T01") {
    input.value = "Summarise the 2019 paper 'Quantum Tea Brewing in Neural Networks' by Dr. R. Menon, including its main results.";
  } else if (type === "T06") {
    input.value = "According to India's 2011 Census, what percentage of the population was left-handed?";
  } else if (type === "T20") {
    input.value = "Why did Akbar order the construction of the Taj Mahal for his wife Mumtaz Mahal?";
  } else if (type === "factual") {
    input.value = "What is the official height of Mount Everest above sea level according to international geodetic surveys?";
  }
}

async function executeLiveTest() {
  const input = document.getElementById("live-question-input");
  const question = input.value.trim();
  const btn = document.getElementById("btn-run-test");
  const loader = document.getElementById("live-test-loader");
  const resultsArea = document.getElementById("live-results-container");

  if (!question) {
    alert("Please enter a question.");
    return;
  }

  // Set loading state
  btn.disabled = true;
  loader.classList.remove("hidden");
  resultsArea.classList.add("hidden");

  try {
    const res = await fetch("/api/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || "Execution failed");
    }

    renderLiveResults(data.evaluations);
    resultsArea.classList.remove("hidden");
  } catch (err) {
    alert(`Error running evaluations: ${err.message}`);
  } finally {
    btn.disabled = false;
    loader.classList.add("hidden");
  }
}

function renderLiveResults(evals) {
  const openaiStack = document.getElementById("openai-eval-cards");
  const geminiStack = document.getElementById("gemini-eval-cards");

  openaiStack.innerHTML = "";
  geminiStack.innerHTML = "";

  evals.forEach(ev => {
    const card = createEvalCard(ev);
    if (ev.model.toLowerCase().includes("openai")) {
      openaiStack.appendChild(card);
    } else {
      geminiStack.appendChild(card);
    }
  });
}

function createEvalCard(ev) {
  const card = document.createElement("div");
  card.className = "eval-card";

  // Badges
  let classBadgeClass = "badge-uncertain";
  const c = ev.classification.toUpperCase();
  if (c === "CORRECT") classBadgeClass = "badge-correct";
  else if (c === "HALLUCINATED") classBadgeClass = "badge-hallucinated";
  else if (c.includes("PARTIAL")) classBadgeClass = "badge-partial";
  else if (c.includes("ERROR")) classBadgeClass = "badge-error";

  let premiseHtml = "";
  if (ev.is_cached_benchmark) {
    premiseHtml += `<span class="box-badge badge-uncertain" style="font-size: 10px;" title="Loaded from verified benchmark record due to live provider quota limits">Benchmark Record</span>`;
  }
  if (ev.premise_valid === true) {
    premiseHtml += `<span class="box-badge badge-hallucinated">Premise: Valid</span>`;
  } else if (ev.premise_valid === false) {
    premiseHtml += `<span class="box-badge badge-correct">Premise: Rejected</span>`;
  }

  let v3ExtraHtml = "";
  if (ev.prompt_version === "V3" && ev.claims_checked) {
    const jsonStr = JSON.stringify({
      claims_checked: ev.claims_checked,
      premise_valid: ev.premise_valid,
      answer: ev.answer || ev.raw_answer
    }, null, 2);

    const detailId = "v3-" + Math.random().toString(36).substring(2, 9);
    v3ExtraHtml = `
      <button class="v3-expand-btn" onclick="toggleV3Details('${detailId}')">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"/></svg>
        Verification Details (Stage 1 & 2 JSON)
      </button>
      <div id="${detailId}" class="v3-details-box hidden">
        <pre>${escapeHtml(jsonStr)}</pre>
      </div>
    `;
  }

  card.innerHTML = `
    <div class="eval-card-header">
      <span class="eval-prompt-tag">${ev.prompt_version} Strategy</span>
      <div class="eval-badges">
        <span class="box-badge ${classBadgeClass}">${ev.classification}</span>
        ${premiseHtml}
      </div>
    </div>
    <div class="eval-card-body">${escapeHtml(ev.raw_answer)}</div>
    <div class="eval-reason"><strong>Analysis:</strong> ${escapeHtml(ev.evaluation_reason || "Evaluated response")}</div>
    ${v3ExtraHtml}
  `;

  return card;
}

function toggleV3Details(id) {
  const el = document.getElementById(id);
  if (el) {
    el.classList.toggle("hidden");
  }
}

// 4. Benchmark Traps Table
async function loadBenchmarkData() {
  try {
    const res = await fetch("/api/questions");
    if (!res.ok) throw new Error("Failed to load questions");
    benchmarkQuestions = await res.json();

    // Populate category dropdown
    const catSelect = document.getElementById("bench-cat-filter");
    const categories = Array.from(new Set(benchmarkQuestions.map(q => q.category))).sort();
    categories.forEach(cat => {
      const opt = document.createElement("option");
      opt.value = cat;
      opt.textContent = cat;
      catSelect.appendChild(opt);
    });

    renderBenchmarkTable(benchmarkQuestions);
  } catch (err) {
    console.error("Benchmark load error:", err);
  }
}

function renderBenchmarkTable(items) {
  const tbody = document.getElementById("traps-tbody");
  tbody.innerHTML = "";

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color: var(--text-muted);">No trap questions found.</td></tr>`;
    return;
  }

  items.forEach(q => {
    const tr = document.createElement("tr");

    let diffColor = "var(--color-correct)";
    if (q.difficulty === "Medium") diffColor = "var(--color-partial)";
    if (q.difficulty === "Hard") diffColor = "var(--color-error)";

    tr.innerHTML = `
      <td><strong style="color: var(--accent-cyan);">${q.id}</strong></td>
      <td>${escapeHtml(q.category)}</td>
      <td><span style="color: ${diffColor}; font-weight: 600;">${q.difficulty}</span></td>
      <td><strong>${escapeHtml(q.question)}</strong></td>
      <td style="font-size: 12px; color: #cbd5e1;">${escapeHtml(q.safe_behavior || q.expected_safe_behavior || "")}</td>
      <td>
        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="testFromBenchmark('${q.id}')">
          Test Live
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterBenchmarkTable() {
  const search = document.getElementById("bench-search").value.toLowerCase();
  const cat = document.getElementById("bench-cat-filter").value;
  const diff = document.getElementById("bench-diff-filter").value;

  const filtered = benchmarkQuestions.filter(q => {
    const matchesSearch = q.id.toLowerCase().includes(search) || q.question.toLowerCase().includes(search) || q.category.toLowerCase().includes(search);
    const matchesCat = !cat || q.category === cat;
    const matchesDiff = !diff || q.difficulty === diff;
    return matchesSearch && matchesCat && matchesDiff;
  });

  renderBenchmarkTable(filtered);
}

function testFromBenchmark(trapId) {
  const q = benchmarkQuestions.find(item => item.id === trapId);
  if (!q) return;

  const input = document.getElementById("live-question-input");
  input.value = q.question;
  switchNav("live-test");
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// 5. Results Table (150 Matrix)
async function loadResultsData() {
  try {
    const res = await fetch("/api/results");
    if (!res.ok) throw new Error("Failed to load results");
    benchmarkResults = await res.json();
    renderResultsTable(benchmarkResults);
  } catch (err) {
    console.error("Results load error:", err);
  }
}

function renderResultsTable(items) {
  const tbody = document.getElementById("results-tbody");
  tbody.innerHTML = "";

  if (items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding: 24px; color: var(--text-muted);">No results found.</td></tr>`;
    return;
  }

  items.forEach((r, idx) => {
    const tr = document.createElement("tr");

    let classBadge = "badge-uncertain";
    const c = (r.classification || "").toUpperCase();
    if (c === "CORRECT") classBadge = "badge-correct";
    else if (c === "HALLUCINATED") classBadge = "badge-hallucinated";
    else if (c.includes("PARTIAL")) classBadge = "badge-partial";
    else if (c.includes("ERROR") || r.is_error) classBadge = "badge-error";

    const isError = r.is_error;
    const statusText = isError 
      ? `<span class="box-badge badge-error">API Error</span>` 
      : `<span class="box-badge badge-correct">Success</span>`;

    let premiseText = "-";
    if (r.premise_valid === true) premiseText = `<span style="color: var(--color-hallucinated); font-weight: 600;">Valid</span>`;
    else if (r.premise_valid === false) premiseText = `<span style="color: var(--color-correct); font-weight: 600;">Rejected</span>`;

    const rawPreview = (r.raw_answer || r.raw_response || "").substring(0, 85) + "...";

    tr.innerHTML = `
      <td><strong style="color: var(--accent-cyan);">${r.question_id || r.trap_id}</strong></td>
      <td style="text-transform: capitalize; font-weight: 500;">${r.model}</td>
      <td><span class="eval-prompt-tag">${r.prompt_version}</span></td>
      <td><span class="box-badge ${classBadge}">${r.classification}</span></td>
      <td>${premiseText}</td>
      <td style="font-family: monospace; font-size: 11px; color: #94a3b8;">${escapeHtml(rawPreview)}</td>
      <td>${statusText}</td>
      <td>
        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="openDetailModal(${idx})">
          View
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterResultsTable() {
  const search = document.getElementById("res-search").value.toLowerCase();
  const model = document.getElementById("res-model-filter").value.toLowerCase();
  const prompt = document.getElementById("res-prompt-filter").value.toUpperCase();
  const cls = document.getElementById("res-class-filter").value.toUpperCase();

  const filtered = benchmarkResults.filter(r => {
    const qid = (r.question_id || r.trap_id || "").toLowerCase();
    const qtext = (r.question || "").toLowerCase();
    const matchesSearch = qid.includes(search) || qtext.includes(search);

    const matchesModel = !model || (r.model || "").toLowerCase() === model;
    const matchesPrompt = !prompt || (r.prompt_version || "").toUpperCase() === prompt;
    
    let matchesClass = true;
    if (cls) {
      if (cls === "API_ERROR") matchesClass = r.is_error || (r.classification || "").includes("ERROR");
      else matchesClass = (r.classification || "").toUpperCase() === cls;
    }

    return matchesSearch && matchesModel && matchesPrompt && matchesClass;
  });

  renderResultsTable(filtered);
}

// 6. Modal Details Viewer
function openDetailModal(index) {
  const item = benchmarkResults[index];
  if (!item) return;

  document.getElementById("modal-title").textContent = `Evaluation: ${item.question_id || item.trap_id} | ${item.model} | ${item.prompt_version}`;
  
  const body = document.getElementById("modal-body");
  
  let v3Section = "";
  if (item.prompt_version === "V3" && item.claims_checked) {
    v3Section = `
      <div style="margin-top: 14px;">
        <h4 style="color: var(--accent-purple); font-size: 13px; margin-bottom: 6px;">V3 Verification Details (Parsed JSON):</h4>
        <pre class="v3-details-box" style="display:block;">${escapeHtml(JSON.stringify({
          claims_checked: item.claims_checked,
          premise_valid: item.premise_valid,
          answer: item.answer
        }, null, 2))}</pre>
      </div>
    `;
  }

  body.innerHTML = `
    <div style="margin-bottom: 12px;">
      <span class="subtext">Question:</span>
      <p style="font-weight: 600; color: #fff; margin-top: 2px;">${escapeHtml(item.question)}</p>
    </div>
    <div style="display: flex; gap: 12px; margin-bottom: 14px;">
      <div><span class="subtext">Classification:</span> <strong>${item.classification}</strong></div>
      <div><span class="subtext">Status:</span> <strong>${item.is_error ? 'API Error' : 'Success'}</strong></div>
      <div><span class="subtext">Timestamp:</span> <span>${item.timestamp}</span></div>
    </div>
    <div style="margin-bottom: 12px;">
      <span class="subtext">Raw Model Response:</span>
      <pre class="v3-details-box" style="display:block; max-height: 250px; white-space: pre-wrap;">${escapeHtml(item.raw_answer || item.raw_response)}</pre>
    </div>
    <div style="margin-bottom: 12px;">
      <span class="subtext">Evaluator Rationale:</span>
      <p style="color: #cbd5e1; border-left: 2px solid var(--accent-blue); padding-left: 8px; margin-top: 4px;">${escapeHtml(item.evaluation_reason || item.rationale || "N/A")}</p>
    </div>
    ${v3Section}
  `;

  document.getElementById("detail-modal").classList.remove("hidden");
}

function closeModal(event) {
  document.getElementById("detail-modal").classList.add("hidden");
}

// Utility: Escape HTML
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
