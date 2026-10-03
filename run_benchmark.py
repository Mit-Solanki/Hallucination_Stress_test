import os
import sys
import json
import time
import datetime
from pathlib import Path

# Set UTF-8 encoding for Windows standard output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from services.model_service import load_prompt, call_model
from services.evaluator import evaluate_classification

QUESTIONS_FILE = Path("data/questions.json")
RESULTS_FILE = Path("data/results.json")

def load_questions():
    if not QUESTIONS_FILE.exists():
        raise FileNotFoundError(f"Questions file not found at {QUESTIONS_FILE}")
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_benchmark_matrix():
    questions = load_questions()
    prompt_versions = ["v1", "v2", "v3"]
    models = ["openai", "gemini"]
    
    matrix = []
    for q in questions:
        for p in prompt_versions:
            for m in models:
                matrix.append({
                    "trap": q,
                    "prompt_version": p,
                    "model": m
                })
    return matrix

def validate_matrix(matrix):
    total = len(matrix)
    unique_tuples = set((item["trap"]["id"], item["prompt_version"], item["model"]) for item in matrix)
    print(f"Matrix verification: {total} total combinations generated, {len(unique_tuples)} unique combinations.", flush=True)
    if total != 150 or len(unique_tuples) != 150:
        raise ValueError(f"Matrix validation failed! Expected 150 unique combinations, found {len(unique_tuples)} unique out of {total}.")
    print("✅ Benchmark matrix validation succeeded: Exactly 150 unique combinations confirmed.\n", flush=True)

def run_benchmark():
    matrix = generate_benchmark_matrix()
    validate_matrix(matrix)
    
    # Load existing results to support resuming and preserving previously run tests
    existing_map = {}
    if RESULTS_FILE.exists():
        try:
            with open(RESULTS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, list):
                    for item in loaded:
                        key = (item.get("question_id") or item.get("trap_id"), (item.get("prompt_version") or "").lower(), (item.get("model") or "").lower())
                        existing_map[key] = item
        except Exception:
            pass

    print("=" * 70, flush=True)
    print(f"STARTING FULL BENCHMARK RUN (150 EVALUATIONS - {len(existing_map)} PRE-EXISTING)", flush=True)
    print("=" * 70, flush=True)
    
    start_time = time.time()
    results = []
    
    for idx, item in enumerate(matrix, 1):
        trap = item["trap"]
        prompt_ver = item["prompt_version"]
        model_name = item["model"]
        trap_id = trap["id"]
        question = trap["question"]
        
        display_model = "OpenAI" if model_name == "openai" else "Gemini"
        display_prompt = prompt_ver.upper()
        key = (trap_id, prompt_ver.lower(), model_name.lower())
        
        # Check if already successfully evaluated in existing results
        if key in existing_map:
            cached = existing_map[key]
            # Ensure required minimum fields exist on cached entry
            cached["timestamp"] = cached.get("timestamp") or datetime.datetime.now(datetime.timezone.utc).isoformat()
            cached["question_id"] = trap_id
            cached["trap_id"] = trap_id
            cached["model"] = model_name
            cached["prompt_version"] = display_prompt
            cached["question"] = question
            cached["raw_answer"] = cached.get("raw_answer") or cached.get("raw_response", "")
            cached["raw_response"] = cached["raw_answer"]
            cached["classification"] = cached.get("classification", "UNCERTAIN")
            cached["evaluation_reason"] = cached.get("evaluation_reason") or cached.get("rationale", "")
            cached["rationale"] = cached["evaluation_reason"]
            cached["premise_valid"] = cached.get("premise_valid")
            cached["is_error"] = cached.get("is_error", False)
            
            results.append(cached)
            print(f"[{idx:03d}/150] {trap_id} | {display_prompt} | {display_model} ... {cached['classification']} (saved)", flush=True)
            continue

        print(f"[{idx:03d}/150] {trap_id} | {display_prompt} | {display_model}", end=" ... ", flush=True)
        
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        raw_answer = ""
        is_error = False
        error_msg = None
        
        try:
            system_prompt = load_prompt(prompt_ver)
            raw_answer = call_model(model_name=model_name, system_prompt=system_prompt, user_prompt=question)
        except Exception as e:
            is_error = True
            error_msg = f"{type(e).__name__}: {str(e)}"
            raw_answer = f"ERROR: {error_msg}"
            print(f"FAILED ({error_msg[:40]})", flush=True)
            
        if not is_error:
            classification, rationale, v3_parsed = evaluate_classification(
                trap_data=trap,
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
                
            print(f"{classification}", flush=True)
        else:
            classification = "UNCERTAIN"
            rationale = f"API call failed: {error_msg}"
            premise_valid = None
            v3_parsed = None

        result_entry = {
            "timestamp": timestamp,
            "question_id": trap_id,
            "trap_id": trap_id,
            "model": model_name,
            "prompt_version": display_prompt,
            "question": question,
            "raw_answer": raw_answer,
            "raw_response": raw_answer,
            "classification": classification,
            "premise_valid": premise_valid,
            "evaluation_reason": rationale,
            "rationale": rationale,
            "is_error": is_error
        }
        
        if prompt_ver == "v3" and v3_parsed:
            result_entry["claims_checked"] = v3_parsed.get("claims_checked")
            result_entry["answer"] = v3_parsed.get("answer")
            
        results.append(result_entry)
        
        # Save incrementally
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
            
        # Pacing
        time.sleep(0.5)

    elapsed = time.time() - start_time
    print("\n" + "=" * 70, flush=True)
    print(f"BENCHMARK COMPLETE IN {elapsed:.1f}s", flush=True)
    print("=" * 70, flush=True)
    
    # Calculate statistics
    total_evals = len(results)
    successful_evals = sum(1 for r in results if not r.get("is_error"))
    failed_evals = sum(1 for r in results if r.get("is_error"))
    
    correct_count = sum(1 for r in results if r.get("classification") == "CORRECT")
    hallucinated_count = sum(1 for r in results if r.get("classification") == "HALLUCINATED")
    partial_count = sum(1 for r in results if r.get("classification") == "PARTIAL_HALLUCINATION")
    uncertain_count = sum(1 for r in results if r.get("classification") == "UNCERTAIN")
    
    print(f"Total evaluations:       {total_evals}", flush=True)
    print(f"Successful evaluations:  {successful_evals}", flush=True)
    print(f"Failed evaluations:      {failed_evals}", flush=True)
    print(f"CORRECT count:           {correct_count}", flush=True)
    print(f"HALLUCINATED count:      {hallucinated_count}", flush=True)
    print(f"PARTIAL_HALLUCINATION:   {partial_count}", flush=True)
    print(f"UNCERTAIN count:         {uncertain_count}", flush=True)
    
    def calc_rate(subset):
        valid = [r for r in subset if not r.get("is_error")]
        if not valid:
            return 0.0, 0
        h_count = sum(1 for r in valid if r.get("classification") in ["HALLUCINATED", "PARTIAL_HALLUCINATION"])
        rate = (h_count / len(valid)) * 100.0
        return rate, len(valid)

    print("\n" + "-" * 70, flush=True)
    print("HALLUCINATION RATES", flush=True)
    print("-" * 70, flush=True)
    
    groups = [
        ("OpenAI overall", [r for r in results if r["model"] == "openai"]),
        ("Gemini overall", [r for r in results if r["model"] == "gemini"]),
        ("V1 overall",     [r for r in results if r["prompt_version"] == "V1"]),
        ("V2 overall",     [r for r in results if r["prompt_version"] == "V2"]),
        ("V3 overall",     [r for r in results if r["prompt_version"] == "V3"]),
        ("OpenAI + V1",    [r for r in results if r["model"] == "openai" and r["prompt_version"] == "V1"]),
        ("OpenAI + V2",    [r for r in results if r["model"] == "openai" and r["prompt_version"] == "V2"]),
        ("OpenAI + V3",    [r for r in results if r["model"] == "openai" and r["prompt_version"] == "V3"]),
        ("Gemini + V1",    [r for r in results if r["model"] == "gemini" and r["prompt_version"] == "V1"]),
        ("Gemini + V2",    [r for r in results if r["model"] == "gemini" and r["prompt_version"] == "V2"]),
        ("Gemini + V3",    [r for r in results if r["model"] == "gemini" and r["prompt_version"] == "V3"]),
    ]
    
    for label, subset in groups:
        rate, n = calc_rate(subset)
        print(f"{label:<16}: {rate:5.1f}% (n={n})", flush=True)
        
    print("-" * 70, flush=True)
    
    # Save final results to data/results.json
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nAll {len(results)} results successfully saved to {RESULTS_FILE}", flush=True)

if __name__ == "__main__":
    run_benchmark()
