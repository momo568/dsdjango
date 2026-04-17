"""
exemple_general.py
Exemple Général — Lance toutes les solutions sur tous les datasets
Montre que le pipeline est universel
"""

import sys
import json
from datetime import datetime

import solution1_no_rag         as sol1
import solution2_prompt_engineering as sol2
import solution3_rag            as sol3
import solution4_auto_correction as sol4


DATASETS = {
    "Django (FR)":  "dataset.json",
    "Django (EN)":  "dataset_english.json",
    "Python (FR)":  "dataset_python.json",
    "ML (FR)":      "dataset_ml.json",
}

SOLUTIONS = {
    "1. Sans RAG":         sol1.main,
    "2. Prompt Eng.":      sol2.main,
    "3. RAG":              sol3.main,
    "4. Auto-Correction":  sol4.main,
}


def get_color(score: float) -> str:
    if score >= 0.55:
        return "🟢"
    elif score >= 0.35:
        return "🟡"
    else:
        return "🔴"


def main():
    print("\n" + "🌍" * 27)
    print("  EXEMPLE GÉNÉRAL — Pipeline Universel")
    print("  Toutes solutions × Tous datasets")
    print("🌍" * 27)

    all_results = {}
    best_overall = {"score": 0, "solution": "", "dataset": ""}

    for dataset_name, dataset_path in DATASETS.items():
        print(f"\n\n{'═' * 55}")
        print(f"  📂 DATASET : {dataset_name}")
        print(f"{'═' * 55}")

        all_results[dataset_name] = {}

        for sol_name, sol_func in SOLUTIONS.items():
            try:
                result = sol_func(
                    dataset_path=dataset_path,
                    limit=3,
                    model="llama3:8b",
                    threshold=0.55
                )
                score = result.get("average_score", 0)
                all_results[dataset_name][sol_name] = score

                if score > best_overall["score"]:
                    best_overall = {
                        "score":    score,
                        "solution": sol_name,
                        "dataset":  dataset_name
                    }
            except Exception as e:
                print(f"  ⚠️  Erreur {sol_name} : {e}")
                all_results[dataset_name][sol_name] = 0.0

    # ── Tableau récapitulatif final ─────────────────────
    print("\n\n" + "🏆" * 27)
    print("  TABLEAU RÉCAPITULATIF FINAL")
    print("🏆" * 27)

    header = f"  {'Dataset':<15}"
    for sol in SOLUTIONS.keys():
        header += f" {sol:<18}"
    print(header)
    print(f"  {'─' * 85}")

    for dataset_name, scores in all_results.items():
        row = f"  {dataset_name:<15}"
        for sol_name in SOLUTIONS.keys():
            score = scores.get(sol_name, 0)
            color = get_color(score)
            row  += f" {color}{score:.3f}{'':12}"
        print(row)

    print(f"\n  🏆 MEILLEURE COMBINAISON :")
    print(f"     Dataset  : {best_overall['dataset']}")
    print(f"     Solution : {best_overall['solution']}")
    print(f"     Score    : {best_overall['score']:.3f}")

    # Exporter rapport final
    report = {
        "results":      all_results,
        "best_overall": best_overall,
        "generated_at": datetime.now().isoformat()
    }
    with open("rapport_general.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n  💾 Rapport final → rapport_general.json")
    print("🏆" * 27)


if __name__ == "__main__":
    main()