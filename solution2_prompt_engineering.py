"""
solution2_prompt_engineering.py
Solution 2 — Prompt Engineering
Compare 4 types de prompts : baseline, expert, few-shot, concis
"""

import json
import random

from evaluation.metrics import MetricsCalculator
from evaluation.release_gate import ReleaseGate


PROMPTS = {
    "baseline": (
        "Tu es un assistant. Réponds en français."
    ),
    "expert": (
        "Tu es un ingénieur Django Senior avec 10 ans d'expérience. "
        "Tu donnes des réponses techniques, précises et concises en français. "
        "Tu vas directement à l'essentiel sans introduction inutile."
    ),
    "few_shot": (
        "Tu es un expert Django. Réponds en français.\n\n"
        "Exemples de bonnes réponses :\n\n"
        "Q: C'est quoi Django ?\n"
        "R: Django est un framework web Python de haut niveau qui encourage "
        "un développement rapide et propre avec un design pragmatique.\n\n"
        "Q: Comment fonctionne l'ORM Django ?\n"
        "R: L'ORM Django mappe les modèles Python aux tables de base de données, "
        "permettant d'écrire des requêtes en Python au lieu de SQL.\n\n"
        "Maintenant réponds à la question suivante de la même manière :"
    ),
    "concis": (
        "Tu es un expert Django. "
        "RÈGLES STRICTES : "
        "1) Réponds en français UNIQUEMENT. "
        "2) Maximum 2 phrases. "
        "3) Pas d'introduction. "
        "4) Utilise les mots techniques exacts."
    ),
}


def get_color(score: float) -> str:
    if score >= 0.55:
        return "🟢"
    elif score >= 0.35:
        return "🟡"
    else:
        return "🔴"


def load_dataset(path: str, limit: int = None) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "dataset" in data:
        data = data["dataset"]
    if limit:
        data = random.sample(data, min(limit, len(data)))
    return data


def evaluate_prompt(prompt_name: str, system_prompt: str,
                    data: list, model: str,
                    calculator: MetricsCalculator,
                    gate: ReleaseGate) -> dict:
    import ollama
    results = []

    print(f"\n  📝 Prompt : {prompt_name}")
    print(f"     {system_prompt[:70]}...")

    for i, item in enumerate(data, 1):
        print(f"     [{i}/{len(data)}] {item['question'][:45]}...")
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": item["question"]}
                ],
                options={"num_predict": 100}
            )
            answer = response.message.content
        except Exception as e:
            print(f"     ⚠️  Erreur : {e}")
            answer = "Erreur"

        metrics = calculator.compute_all(
            question=item["question"],
            prediction=answer,
            reference=item.get("expected_answer", "")
        )
        results.append({**item, "answer": answer, **metrics})

    scores = gate.compute_global_score(results)
    score  = scores["average_score"]
    passed = score >= gate.threshold
    color  = get_color(score)
    print(f"     {color} Score : {score:.3f} ({'✅ DEPLOY' if passed else '❌ BLOCK'})")

    return {"prompt_name": prompt_name, "system_prompt": system_prompt,
            "model": model, **scores, "passed": passed}


def main(dataset_path: str = "dataset.json", limit: int = 5,
         model: str = "llama3:8b", threshold: float = 0.55):

    print("\n" + "📝" * 27)
    print("  SOLUTION 2 — PROMPT ENGINEERING")
    print("  Compare 4 types de prompts")
    print("📝" * 27)
    print(f"  📂 Dataset : {dataset_path}")
    print(f"  🤖 Modèle  : {model}")
    print(f"  🎯 Seuil   : {threshold}")

    data = load_dataset(dataset_path, limit)
    print(f"  🔢 Questions : {len(data)}")

    calculator = MetricsCalculator()
    gate       = ReleaseGate(threshold=threshold)
    results    = []

    for name, prompt in PROMPTS.items():
        result = evaluate_prompt(name, prompt, data, model, calculator, gate)
        results.append(result)

    winner = max(results, key=lambda x: x["average_score"])

    print("\n" + "=" * 60)
    print("  📊 RÉSULTATS — PROMPT ENGINEERING")
    print("=" * 60)
    print(f"  {'Prompt':<15} {'BLEU':<8} {'ROUGE':<8} {'Judge':<8} {'Score':<8} {'Statut'}")
    print(f"  {'─' * 58}")

    for r in results:
        score  = r["average_score"]
        color  = get_color(score)
        flag   = " 🏆" if r["prompt_name"] == winner["prompt_name"] else ""
        status = "DEPLOY ✅" if r["passed"] else "BLOCK  ❌"
        print(f"  {r['prompt_name']:<15} "
              f"{r['bleu_score']:<8.3f} "
              f"{r['rouge_score']:<8.3f} "
              f"{r['llm_judge_score']:<8.3f} "
              f"{color}{score:<7.3f} {status}{flag}")

    print(f"\n  🏆 Meilleur prompt : {winner['prompt_name']}")
    print(f"  📊 Score           : {winner['average_score']:.3f}")
    print(f"  💡 Conseil         : Utiliser '{winner['prompt_name']}' en production")
    print("=" * 60)

    report = {"solution": "Prompt Engineering", "dataset": dataset_path,
              "model": model, "results": results,
              "winner": winner["prompt_name"],
              "winner_score": winner["average_score"]}

    with open("results_solution2.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n  💾 Rapport exporté → results_solution2.json")

    return report


if __name__ == "__main__":
    import argparse
    import sys
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset",   default="dataset.json")
    parser.add_argument("--limit",     type=int, default=5)
    parser.add_argument("--model",     default="llama3:8b")
    parser.add_argument("--threshold", type=float, default=0.55)
    args = parser.parse_args()
    report = main(args.dataset, args.limit, args.model, args.threshold)
    
    # Check if the winning prompt actually passed the threshold
    winner_passed = False
    for res in report["results"]:
        if res["prompt_name"] == report["winner"] and res["passed"]:
            winner_passed = True
            break
            
    sys.exit(0 if winner_passed else 1)