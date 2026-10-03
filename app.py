import os
import json
import datetime
from pathlib import Path
from flask import Flask, render_template, request, jsonify

from services.model_service import load_prompt, call_model
from services.evaluator import evaluate_classification

app = Flask(__name__)

DATA_DIR = Path("data")
QUESTIONS_FILE = DATA_DIR / "questions.json"
RESULTS_FILE = DATA_DIR / "results.json"

def get_questions():
    if not QUESTIONS_FILE.exists():
        return []
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_results():
    if not RESULTS_FILE.exists():
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/questions", methods=["GET"])
def api_questions():
    return jsonify(get_questions())

@app.route("/api/results", methods=["GET"])
def api_results():
    return jsonify(get_results())

@app.route("/api/statistics", methods=["GET"])
def api_statistics():
    results = get_results()
    questions = get_questions()
    
    total_combinations = len(results) if results else 150
    total_traps = len(questions) if questions else 25
    
    successful_list = [r for r in results if not r.get("is_error")]
    failed_list = [r for r in results if r.get("is_error")]
    
    successful_count = len(successful_list)
    failed_count = len(failed_list)
    
    # Classification breakdown among successful evaluations
    correct_count = sum(1 for r in successful_list if r.get("classification") == "CORRECT")
    hallucinated_count = sum(1 for r in successful_list if r.get("classification") == "HALLUCINATED")
    partial_count = sum(1 for r in successful_list if r.get("classification") == "PARTIAL_HALLUCINATION")
    uncertain_count = sum(1 for r in successful_list if r.get("classification") == "UNCERTAIN")
    
    def calc_rate(subset):
        valid = [r for r in subset if not r.get("is_error")]
        if not valid:
            return 0.0, 0
        h = sum(1 for r in valid if r.get("classification") in ["HALLUCINATED", "PARTIAL_HALLUCINATION"])
        return round((h / len(valid)) * 100.0, 1), len(valid)

    # Hallucination rates strictly on successful runs
    rate_openai, n_openai = calc_rate([r for r in results if r.get("model") == "openai"])
    rate_gemini, n_gemini = calc_rate([r for r in results if r.get("model") == "gemini"])
    
    rate_v1, n_v1 = calc_rate([r for r in results if (r.get("prompt_version") or "").upper() == "V1"])
    rate_v2, n_v2 = calc_rate([r for r in results if (r.get("prompt_version") or "").upper() == "V2"])
    rate_v3, n_v3 = calc_rate([r for r in results if (r.get("prompt_version") or "").upper() == "V3"])
    
    rate_o_v1, n_o_v1 = calc_rate([r for r in results if r.get("model") == "openai" and (r.get("prompt_version") or "").upper() == "V1"])
    rate_o_v2, n_o_v2 = calc_rate([r for r in results if r.get("model") == "openai" and (r.get("prompt_version") or "").upper() == "V2"])
    rate_o_v3, n_o_v3 = calc_rate([r for r in results if r.get("model") == "openai" and (r.get("prompt_version") or "").upper() == "V3"])
    
    rate_g_v1, n_g_v1 = calc_rate([r for r in results if r.get("model") == "gemini" and (r.get("prompt_version") or "").upper() == "V1"])
    rate_g_v2, n_g_v2 = calc_rate([r for r in results if r.get("model") == "gemini" and (r.get("prompt_version") or "").upper() == "V2"])
    rate_g_v3, n_g_v3 = calc_rate([r for r in results if r.get("model") == "gemini" and (r.get("prompt_version") or "").upper() == "V3"])

    stats = {
        "total_combinations": total_combinations,
        "successful_evaluations": successful_count,
        "api_failures": failed_count,
        "trap_questions": total_traps,
        "transparency_note": f"{total_combinations} benchmark combinations • {successful_count} successful model evaluations currently available",
        "classifications": {
            "correct": correct_count,
            "hallucinated": hallucinated_count,
            "partial_hallucination": partial_count,
            "uncertain": uncertain_count,
            "api_errors": failed_count
        },
        "hallucination_rates": {
            "openai_overall": {"rate": rate_openai, "sample_size": n_openai},
            "gemini_overall": {"rate": rate_gemini, "sample_size": n_gemini},
            "v1_overall": {"rate": rate_v1, "sample_size": n_v1},
            "v2_overall": {"rate": rate_v2, "sample_size": n_v2},
            "v3_overall": {"rate": rate_v3, "sample_size": n_v3},
            "openai_v1": {"rate": rate_o_v1, "sample_size": n_o_v1},
            "openai_v2": {"rate": rate_o_v2, "sample_size": n_o_v2},
            "openai_v3": {"rate": rate_o_v3, "sample_size": n_o_v3},
            "gemini_v1": {"rate": rate_g_v1, "sample_size": n_g_v1},
            "gemini_v2": {"rate": rate_g_v2, "sample_size": n_g_v2},
            "gemini_v3": {"rate": rate_g_v3, "sample_size": n_g_v3}
        }
    }
    return jsonify(stats)

@app.route("/api/test", methods=["POST"])
def api_test():
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    
    if not question:
        return jsonify({"error": "Please enter a question."}), 400
        
    if len(question) > 2000:
        return jsonify({"error": "Question is too long (maximum 2000 characters)."}), 400

    # Match question against known traps if possible
    questions = get_questions()
    matched_trap = next((q for q in questions if q.get("question", "").strip().lower() == question.lower()), None)
    if not matched_trap:
        # Check partial or substring match
        matched_trap = next((q for q in questions if q.get("question", "").strip() in question or question in q.get("question", "").strip()), None)
    
    trap_data = matched_trap if matched_trap else {
        "id": "UNSEEN",
        "question": question,
        "category": "User Input",
        "type": "Custom"
    }

    test_matrix = [
        ("openai", "v1"),
        ("openai", "v2"),
        ("openai", "v3"),
        ("gemini", "v1"),
        ("gemini", "v2"),
        ("gemini", "v3")
    ]
    
    evaluations = []
    
    for model_name, prompt_ver in test_matrix:
        display_model = "OpenAI" if model_name == "openai" else "Gemini"
        display_prompt = prompt_ver.upper()
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        is_error = False
        error_msg = None
        raw_answer = ""
        
        try:
            system_prompt = load_prompt(prompt_ver)
            raw_answer = call_model(model_name=model_name, system_prompt=system_prompt, user_prompt=question, max_retries=1)
        except Exception as e:
            is_error = True
            err_type = type(e).__name__
            err_str = str(e)
            if "RESOURCE_EXHAUSTED" in err_str or "Quota exceeded" in err_str or "rate_limit" in err_str or "429" in err_str:
                error_msg = "API unavailable / quota exceeded"
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                error_msg = "Model service temporarily unavailable (503)"
            else:
                error_msg = f"{err_type}: {err_str[:80]}"
            raw_answer = f"API Error: {error_msg}"

        if is_error and matched_trap:
            # If live API quota is exhausted, check if we have the actual recorded benchmark evaluation
            all_results = get_results()
            cached_eval = next((
                r for r in all_results 
                if (r.get("question_id") == matched_trap.get("id") or r.get("trap_id") == matched_trap.get("id"))
                and (r.get("model") or "").lower() == model_name.lower()
                and (r.get("prompt_version") or "").lower() == prompt_ver.lower()
                and not r.get("is_error")
            ), None)

            if cached_eval:
                c_item = {
                    "model": display_model,
                    "prompt_version": display_prompt,
                    "question": question,
                    "raw_answer": cached_eval.get("raw_answer") or cached_eval.get("raw_response", ""),
                    "classification": cached_eval.get("classification", "CORRECT"),
                    "premise_valid": cached_eval.get("premise_valid"),
                    "evaluation_reason": cached_eval.get("evaluation_reason") or cached_eval.get("rationale", ""),
                    "is_error": False,
                    "is_cached_benchmark": True,
                    "timestamp": cached_eval.get("timestamp", timestamp)
                }
                if prompt_ver == "v3":
                    c_item["claims_checked"] = cached_eval.get("claims_checked", [])
                    c_item["answer"] = cached_eval.get("answer", "")
                evaluations.append(c_item)
                continue

        if not is_error:
            classification, rationale, v3_parsed = evaluate_classification(
                trap_data=trap_data,
                prompt_version=prompt_ver,
                raw_response=raw_answer
            )
            premise_valid = None
            if prompt_ver == "v3" and v3_parsed:
                premise_valid = v3_parsed.get("premise_valid")
            elif classification == "CORRECT":
                premise_valid = False
            elif classification == "HALLUCINATED":
                premise_valid = True
            elif classification == "PARTIAL_HALLUCINATION":
                premise_valid = False
        else:
            classification = "API ERROR"
            rationale = error_msg
            premise_valid = None
            v3_parsed = None

        eval_item = {
            "model": display_model,
            "prompt_version": display_prompt,
            "question": question,
            "raw_answer": raw_answer,
            "classification": classification,
            "premise_valid": premise_valid,
            "evaluation_reason": rationale,
            "is_error": is_error,
            "timestamp": timestamp
        }
        
        if prompt_ver == "v3" and v3_parsed:
            eval_item["claims_checked"] = v3_parsed.get("claims_checked", [])
            eval_item["answer"] = v3_parsed.get("answer", "")
            
        evaluations.append(eval_item)
        
    return jsonify({
        "success": True,
        "question": question,
        "trap_id": trap_data.get("id"),
        "evaluations": evaluations
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
