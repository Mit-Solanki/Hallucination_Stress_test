import json
from pathlib import Path

RESULTS_FILE = Path("data/results.json")

def analyze_benchmark_results():
    if not RESULTS_FILE.exists():
        print(f"Results file not found: {RESULTS_FILE}")
        return

    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

    total_evals = len(results)
    successful = [r for r in results if not r.get("is_error")]
    failed = [r for r in results if r.get("is_error")]

    print("=" * 70)
    print("HALLUCIGUARD BENCHMARK ANALYSIS")
    print("=" * 70)
    print(f"Total Combinations:       {total_evals}")
    print(f"Successful Evaluations:   {len(successful)}")
    print(f"API Quota Failures:       {len(failed)}")
    print("-" * 70)

    # Classifications among successful
    classifications = {}
    for r in successful:
        c = r.get("classification", "UNCERTAIN")
        classifications[c] = classifications.get(c, 0) + 1

    print("CLASSIFICATION DISTRIBUTION (Successful Evaluations):")
    for c, count in sorted(classifications.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(successful)) * 100 if successful else 0
        print(f"  {c:<22}: {count:>3} ({pct:>5.1f}%)")

    def calc_rate(subset):
        valid = [r for r in subset if not r.get("is_error")]
        if not valid:
            return 0.0, 0
        h_count = sum(1 for r in valid if r.get("classification") in ["HALLUCINATED", "PARTIAL_HALLUCINATION"])
        return (h_count / len(valid)) * 100.0, len(valid)

    print("-" * 70)
    print("HALLUCINATION RATES ((Hallucinated + Partial) / Total Valid * 100):")
    
    slices = [
        ("OpenAI Overall", [r for r in results if r.get("model") == "openai"]),
        ("Gemini Overall", [r for r in results if r.get("model") == "gemini"]),
        ("V1 (Basic) Overall", [r for r in results if (r.get("prompt_version") or "").upper() == "V1"]),
        ("V2 (Fact-Check) Overall", [r for r in results if (r.get("prompt_version") or "").upper() == "V2"]),
        ("V3 (Defensive) Overall", [r for r in results if (r.get("prompt_version") or "").upper() == "V3"]),
        ("OpenAI + V1", [r for r in results if r.get("model") == "openai" and (r.get("prompt_version") or "").upper() == "V1"]),
        ("OpenAI + V2", [r for r in results if r.get("model") == "openai" and (r.get("prompt_version") or "").upper() == "V2"]),
        ("OpenAI + V3", [r for r in results if r.get("model") == "openai" and (r.get("prompt_version") or "").upper() == "V3"]),
        ("Gemini + V1", [r for r in results if r.get("model") == "gemini" and (r.get("prompt_version") or "").upper() == "V1"]),
        ("Gemini + V2", [r for r in results if r.get("model") == "gemini" and (r.get("prompt_version") or "").upper() == "V2"]),
        ("Gemini + V3", [r for r in results if r.get("model") == "gemini" and (r.get("prompt_version") or "").upper() == "V3"]),
    ]

    for label, subset in slices:
        rate, n = calc_rate(subset)
        print(f"  {label:<25}: {rate:>5.1f}% (n={n})")

    print("=" * 70)

if __name__ == "__main__":
    analyze_benchmark_results()
