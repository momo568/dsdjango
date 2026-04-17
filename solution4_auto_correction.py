"""
solution4_auto_correction.py
Solution 4 — Auto-Correction (Self-Refinement)
L'IA corrige elle-même sa réponse si le score est trop bas
"""

import sys
import json
import random

from evaluation.metrics import MetricsCalculator
from evaluation.release_gate import ReleaseGate


def call_llm(question: str, system_prompt: str,
             model: str, max_tokens: int = 150) -> str:
    import ollama
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": question}
            ],
            options={"num_predict": max_tokens}
        )
        return response.message.content
    except Exception as e:
        return f"Erreur : {e}"


def auto_correct(question: str, answer: str, score: float,
                 expected: str, model: str) -> str:
    """
    Si le score est bas → demande à l'IA de corriger sa réponse.
    """
    correction_prompt = (
        f"Tu as répondu à cette question : '{question}'\n"
        f"Ta réponse : '{answer}'\n"
        f"Score obtenu : {score:.2f} (insuffisant)\n"
        f"Réponse attendue ressemble à : '{expected[:100]}...'\n\n"
        f"Améliore ta réponse pour qu'elle soit plus précise, "
        f"concise et proche de la réponse attendue. "
        f"Réponds directement sans introduction."
    )
    return call_llm(question, correction_prompt, model)


def main(dataset_path="dataset.json", limit=5,
         model="llama3:8b", threshold=0.55,
         correction_threshold=0.40, max_iterations=2):

    print("\n" + "🔄" * 27)
    print("  SOLUTION 4 — AUTO-CORRECTION")
    print("  L'IA corrige elle-même ses réponses")
    print("🔄" * 27)
    print(f"  📂 Dataset              : {dataset_path}")
    print(f"  🤖 Modèle               : {model}")
    print(f"  🎯 Seuil correction     : {correction_threshold}")
    print(f"  🔁 Max itérations       : {max_iterations}")

    # Charger dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "dataset" in data:
        data = data["dataset"]
    if limit:
        data = random.sample(data, min(limit, len(data)))
    print(f"  🔢 Questions : {len(data)}")

    calculator  = MetricsCalculator()
    gate        = ReleaseGate(threshold=threshold)
    llm_results = []

    print("\n" + "=" * 55)
    print("  📤 Envoi + Auto-Correction")
    print("=" * 55)

    base_prompt = (
        "Tu es un expert Django. "
        "Réponds en français de manière concise et précise."
    )

    for i, item in enumerate(data, 1):
        question = item["question"]
        expected = item.get("expected_answer", "")

        print(f"\n  [{i}/{len(data)}] {question[:50]}...")

        # Réponse initiale
        answer = call_llm(question, base_prompt, model)

        # Calculer score initial
        metrics = calculator.compute_all(question, answer, expected)
        score   = metrics["average_score"]
        print(f"     Itération 1 → score : {score:.3f}")

        # Boucle de correction
        for iteration in range(max_iterations):
            if score >= correction_threshold:
                print(f"     ✅ Score suffisant — pas de correction")
                break

            print(f"     🔄 Score bas ({score:.3f}) → correction...")
            answer  = auto_correct(question, answer, score, expected, model)
            metrics = calculator.compute_all(question, answer, expected)
            score   = metrics["average_score"]
            print(f"     Itération {iteration + 2} → score : {score:.3f}")

        llm_results.append({
            "question":        question,
            "answer":          answer,
            "expected_answer": expected,
            **metrics
        })

    # Calculer métriques globales
    global_scores = gate.compute_global_score(llm_results)
    gate_result   = gate.apply_gate(global_scores)

    # Exporter
    gate.export_results(gate_result, "results_solution4.json")

    print(f"\n  🔄 RÉSULTAT SOLUTION 4 (Auto-Correction)")
    print(f"  📊 Score : {gate_result['average_score']}")
    print(f"  📋 Décision : {gate_result['decision']}")
    print("=" * 55)

    return gate_result


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",    default="dataset.json")
    parser.add_argument("--limit",      type=int,   default=5)
    parser.add_argument("--model",      default="llama3:8b")
    parser.add_argument("--threshold",  type=float, default=0.55)
    parser.add_argument("--max-iter",   type=int,   default=2)
    args = parser.parse_args()
    result = main(args.dataset, args.limit, args.model,
         args.threshold, max_iterations=args.max_iter)
    sys.exit(0 if result["passed"] else 1)