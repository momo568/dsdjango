"""
solution1_no_rag.py
Solution 1 — Sans RAG (Baseline)
Lance le pipeline sans aucune amélioration
"""

import sys
import json
import random

from evaluation.llm_caller import LLMCaller
from evaluation.metrics import MetricsCalculator
from evaluation.release_gate import ReleaseGate


def main(dataset_path: str = "dataset.json", limit: int = 5,
         model: str = "llama3:8b", threshold: float = 0.55):

    print("\n" + "🔴" * 27)
    print("  SOLUTION 1 — SANS RAG (Baseline)")
    print("  Aucune amélioration — résultat brut")
    print("🔴" * 27)
    print(f"  📂 Dataset : {dataset_path}")
    print(f"  🤖 Modèle  : {model}")

    # Charger dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "dataset" in data:
        data = data["dataset"]
    if limit:
        data = random.sample(data, min(limit, len(data)))
    print(f"  🔢 Questions : {len(data)}")

    # Appeler LLM sans RAG
    import ollama
    llm_results = []
    print("\n" + "=" * 55)
    print("  📤 Envoi des questions au LLM — mode brut")
    print("=" * 55)

    for i, item in enumerate(data, 1):
        print(f"  [{i}/{len(data)}] {item['question'][:50]}...")
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": "Tu es un assistant. Réponds en français."},
                    {"role": "user",   "content": item["question"]}
                ],
                options={"num_predict": 150}
            )
            answer = response.message.content
            status = "success"
        except Exception as e:
            print(f"  ⚠️  Erreur : {e}")
            answer = "Erreur"
            status = "error"

        llm_results.append({
            "question":        item["question"],
            "answer":          answer,
            "expected_answer": item.get("expected_answer", ""),
            "status":          status,
        })

    # Calculer métriques
    calculator = MetricsCalculator()
    evaluated  = calculator.evaluate_all_results(llm_results)

    # Porte de release
    gate          = ReleaseGate(threshold=threshold)
    global_scores = gate.compute_global_score(evaluated)
    gate_result   = gate.apply_gate(global_scores)

    # Exporter
    gate.export_results(gate_result, "results_solution1.json")

    print(f"\n  🔴 RÉSULTAT SOLUTION 1 (Sans RAG)")
    print(f"  📊 Score : {gate_result['average_score']}")
    
    if gate_result['decision'] == "BLOCK":
        print(f"  \033[91m\033[1m📋 Décision : {gate_result['decision']}\033[0m")
    else:
        print(f"  \033[92m📋 Décision : {gate_result['decision']}\033[0m")
    
    print("=" * 55)

    return gate_result


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",   default="dataset.json")
    parser.add_argument("--limit",     type=int, default=5)
    parser.add_argument("--model",     default="llama3:8b")
    parser.add_argument("--threshold", type=float, default=0.55)
    args = parser.parse_args()
    result = main(args.dataset, args.limit, args.model, args.threshold)
    sys.exit(0 if result["passed"] else 1)