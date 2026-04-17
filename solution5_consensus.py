"""
solution5_consensus.py
Solution 5 — Consensus / Model Ensembling
Interroge 3 modèles différents (ou 3 fois avec des configurations différentes) et fusionne les résultats.
"""

import sys
import json
import random

from evaluation.metrics import MetricsCalculator
from evaluation.release_gate import ReleaseGate


def call_llm(question: str, system_prompt: str, model: str) -> str:
    import ollama
    try:
        response = ollama.chat(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": question}
            ],
            options={"num_predict": 100}
        )
        return response.message.content
    except Exception as e:
        return f"Erreur avec {model}: {e}"


def get_consensus(question: str, answers: list, judge_model: str) -> str:
    """Demande au modèle juge de créer la meilleure réponse à partir des 3 propositions."""
    prompt = (
        f"Tu es un juge expert. Voici 3 réponses possibles à la question : '{question}'.\n\n"
        f"Réponse 1 : {answers[0]}\n"
        f"Réponse 2 : {answers[1]}\n"
        f"Réponse 3 : {answers[2]}\n\n"
        "Fais une synthèse courte, exacte et précise en français, en prenant les meilleures informations des 3."
    )
    return call_llm(question, prompt, model=judge_model)


def main(dataset_path="dataset.json", limit=5, threshold=0.55):
    # Liste de modèles par défaut (tu peux modifier ceux que tu as en local)
    models_to_test = ["llama3.2:1b", "mistral:latest", "llama3:8b"]
    judge_model = "llama3.2:1b"

    print("\n" + "🤝" * 27)
    print("  SOLUTION 5 — CONSENSUS (ENSEMBLING)")
    print("  Interroge plusieurs modèles et fait une synthèse")
    print("🤝" * 27)
    print(f"  📂 Dataset : {dataset_path}")
    print(f"  🤖 Modèles : {', '.join(models_to_test)}")
    print(f"  ⚖️ Juge    : {judge_model}")

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "dataset" in data:
        data = data["dataset"]
    if limit:
        data = random.sample(data, min(limit, len(data)))
    print(f"  🔢 Questions : {len(data)}")

    calculator = MetricsCalculator()
    gate       = ReleaseGate(threshold=threshold)
    llm_results = []
    base_prompt = "Tu es un expert Django. Réponds de manière courte et juste en français."

    print("\n" + "=" * 55)
    print("  📤 Génération multiple et Synthèse")
    print("=" * 55)

    for i, item in enumerate(data, 1):
        question = item["question"]
        expected = item.get("expected_answer", "")
        print(f"\n  [{i}/{len(data)}] {question[:50]}...")

        answers = []
        for model in models_to_test:
            ans = call_llm(question, base_prompt, model)
            answers.append(ans)
            print(f"     ✅ {model} a répondu.")

        print(f"     🔄 Fusion en cours par {judge_model}...")
        final_answer = get_consensus(question, answers, judge_model)
        
        metrics = calculator.compute_all(question, final_answer, expected)
        score   = metrics["average_score"]
        print(f"     📊 Score Final (Consensus) : {score:.3f}")

        llm_results.append({
            "question":        question,
            "answer":          final_answer,
            "answers_raw":     answers,
            "expected_answer": expected,
            **metrics
        })

    global_scores = gate.compute_global_score(llm_results)
    gate_result   = gate.apply_gate(global_scores)

    gate.export_results(gate_result, "results_solution5.json")

    print(f"\n  🤝 RÉSULTAT SOLUTION 5 (Consensus)")
    print(f"  📊 Score : {gate_result['average_score']}")
    print(f"  📋 Décision : {gate_result['decision']}")
    print("=" * 55)

    return gate_result


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",   default="dataset.json")
    parser.add_argument("--limit",     type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.55)
    args = parser.parse_args()
    result = main(args.dataset, args.limit, args.threshold)
    sys.exit(0 if result["passed"] else 1)
