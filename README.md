# 🛡️ HalluciGuard — Hallucination Stress Test

HalluciGuard is an empirical evaluation framework and interactive stress-testing suite designed to measure and mitigate Large Language Model (LLM) hallucinations. It evaluates how different prompting strategies affect model reliability when exposed to fabricated entities, counterfactual premises, and impossible scenarios.

---

## 📌 Project Overview

When prompted with questions containing false premises (e.g., fictitious research papers, non-existent laws, or historical anachronisms), standard LLMs often exhibit **conversational compliance**—accepting the premise and fabricating plausible-sounding details. 

HalluciGuard systematically benchmarks and visualizes model vulnerability across:
- **25 Curated Trap Questions** ($T01 - T25$)
- **3 Prompting Strategies** ($V1$ Basic, $V2$ Fact-Check, $V3$ Defensive)
- **2 State-of-the-Art LLMs** (OpenAI `gpt-6-luna` & Google Gemini `gemini-3.8-flash`)
- **150 Total Evaluation Combinations** ($25 \times 3 \times 2$)

---

## 🔬 Prompting Strategies

1. **V1 — Basic (Baseline):**
   Standard helpful assistant prompt without explicit verification constraints. Demonstrates baseline susceptibility to conversational traps.
2. **V2 — Fact-Check (Verification-Aware):**
   Instructs the model to check every named entity, citation, and date before answering, explicitly refusing to answer if unverifiable.
3. **V3 — Defensive (Structured Two-Stage Reasoning):**
   Enforces a two-stage reasoning protocol (**Stage 1: Claim Verification** $\rightarrow$ **Stage 2: Final Answer**) and outputs machine-parseable JSON (`claims_checked`, `premise_valid`, `answer`).

---

## 📊 Benchmark Findings

From the 150 benchmark combinations executed:
- **Available Successful Evaluations:** 43
- **Provider API Quota Failures:** 107 (daily free-tier rate/quota limits reached; strictly segregated from model evaluations)
- **OpenAI Overall Hallucination Rate:** 8.1% ($n=37$)
- **Prompt V2 Effect:** Reduced OpenAI hallucinations to **0.0%** across tested traps.

$$\text{Hallucination Rate} = \frac{\text{HALLUCINATED} + \text{PARTIAL\_HALLUCINATION}}{\text{Total Valid Evaluations}} \times 100$$

---

## 🚀 Local Quickstart

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/Mit-Solanki/Hallucination_Stress_test.git
cd Hallucination_Stress_test

# Create virtual environment
python -m venv venv
# Activate on Windows:
.\venv\Scripts\activate
# Activate on Linux/macOS:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your API credentials:
```bash
cp .env.example .env
```
Edit `.env`:
```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-6-luna

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.8-flash
```

### 3. Run Application
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.

---

## 📁 Repository Structure

```text
HalluciGuard/
├── app.py                     # Flask web server & REST API
├── run_benchmark.py           # 150-combination benchmark runner
├── analyze_results.py         # Statistical analysis script
├── parse_traps.py             # Dataset extraction pipeline
├── requirements.txt           # Python package dependencies
├── .env.example               # Template environment configuration
├── .gitignore                 # Excludes .env, venv, and cache files
├── data/
│   ├── questions.json         # 25 curated trap questions
│   └── results.json           # 150 benchmark evaluation records
├── prompts/
│   ├── basic.txt              # V1 Basic prompt
│   ├── fact_check.txt         # V2 Fact-Check prompt
│   └── defensive.txt          # V3 Defensive two-stage prompt
├── services/
│   ├── model_service.py       # OpenAI & Gemini API client service
│   └── evaluator.py           # Ground-truth semantic classifier
├── templates/
│   └── index.html             # Single-page dashboard interface
└── static/
    ├── style.css              # Dark-mode dashboard stylesheet
    └── app.js                 # Interactive UI controller & Chart.js
```

---

## 👥 Team & Contribution Areas

| Member | Role | Primary Contributions |
| :--- | :--- | :--- |
| **Mit Solanki** | Prompt Engineering | Prompt design, prompt refinement, testing constraints (V1, V2, V3) |
| **Mayur Khandla** | Core Development | Flask prototype, model integration, evaluation pipeline, API routes |
| **Tanvi Kakadiya** | Research & Analysis | 25 trap questions dataset, problem analysis, benchmark execution |
| **Sai Prashanth** | UI & Documentation | Dashboard UI, interactive live-test, Chart.js, workflow and documentation |

---

## ⚖️ License
MIT License. Developed for research and educational stress-testing of LLMs.
