import os
import sys
import json
import datetime
from pathlib import Path

# Set UTF-8 encoding for standard output if running on Windows
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

def run_single_evaluation(trap: dict, prompt_version: str, model_name: str) -> dict:
    trap_id = trap.get("id")
    question = trap.get("question")
    
    # 1. Load exact prompt
    system_prompt = load_prompt(prompt_version)
    
    # User prompt format: {QUESTION}
    user_prompt = question
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # 2. Call model
    print(f"-> Calling {model_name.upper()} with {prompt_version.upper()} for {trap_id}...")
    try:
        raw_response = call_model(model_name=model_name, system_prompt=system_prompt, user_prompt=user_prompt)
    except Exception as e:
        raw_response = f"ERROR: {type(e).__name__}: {str(e)}"
    
    # 3. Evaluate and classify
    classification, rationale, v3_parsed = evaluate_classification(
        trap_data=trap,
        prompt_version=prompt_version,
        raw_response=raw_response
    )
    
    result = {
        "trap_id": trap_id,
        "prompt_version": prompt_version.upper(),
        "model": model_name.lower(),
        "question": question,
        "raw_response": raw_response,
        "classification": classification,
        "rationale": rationale,
        "timestamp": timestamp
    }
    
    if prompt_version.lower() == "v3" and v3_parsed:
        result["claims_checked"] = v3_parsed.get("claims_checked")
        result["premise_valid"] = v3_parsed.get("premise_valid")
        result["answer"] = v3_parsed.get("answer")
        
    return result

def run_current_task_test(target_trap_id: str = "T01"):
    """
    Executes the current task:
    Runs only ONE trap question (default T01) through:
    1. V1 + OpenAI
    2. V1 + Gemini
    3. V2 + OpenAI
    4. V2 + Gemini
    5. V3 + OpenAI
    6. V3 + Gemini
    Total: exactly 6 API calls.
    """
    questions = load_questions()
    trap = next((q for q in questions if q.get("id") == target_trap_id), None)
    if not trap:
        raise ValueError(f"Trap {target_trap_id} not found in {QUESTIONS_FILE}")
        
    print("=" * 70)
    print(f"RUNNING 6-CALL VERIFICATION TEST ON TRAP: {trap['id']}")
    print(f"Category: {trap.get('category')} | Type: {trap.get('type')}")
    print(f"Question: {trap.get('question')}")
    print(f"False Premise: {trap.get('false_premise')}")
    print("=" * 70)
    
    test_matrix = [
        ("v1", "openai"),
        ("v1", "gemini"),
        ("v2", "openai"),
        ("v2", "gemini"),
        ("v3", "openai"),
        ("v3", "gemini")
    ]
    
    results = []
    
    for prompt_ver, model_name in test_matrix:
        res = run_single_evaluation(trap, prompt_ver, model_name)
        results.append(res)
        
        # Display each result cleanly
        print("\n" + "-" * 70)
        print(f"Trap ID:        {res['trap_id']}")
        print(f"Prompt Version: {res['prompt_version']}")
        print(f"Model:          {res['model']}")
        print(f"Timestamp:      {res['timestamp']}")
        print(f"Classification: {res['classification']}")
        print(f"Rationale:      {res['rationale']}")
        if "claims_checked" in res:
            print(f"Claims Checked: {json.dumps(res['claims_checked'], ensure_ascii=False)}")
            print(f"Premise Valid:  {res['premise_valid']}")
            print(f"Parsed Answer:  {res['answer']}")
        print("Raw Response:")
        print(res["raw_response"].strip())
        print("-" * 70)
        
    # Save results to data/results.json
    RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"\n[SUCCESS] All 6 evaluation results saved to {RESULTS_FILE}")
    return results

if __name__ == "__main__":
    trap_id = sys.argv[1] if len(sys.argv) > 1 else "T01"
    run_current_task_test(trap_id)
