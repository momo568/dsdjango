"""
evaluation/version_comparator.py
Étudiant 2 — Comparaison de prompts ET de modèles
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluation.metrics import MetricsCalculator
from evaluation.release_gate import ReleaseGate


class VersionComparator:

    def __init__(self, threshold: float = 0.40):
        self.calculator = MetricsCalculator()
        self.gate       = ReleaseGate(threshold=threshold)

    def evaluate_version(self, version_name: str, system_prompt: str,
                         dataset: list, model: str = "llama3.2:1b") -> dict:
        print(f"\n  🔍 Évaluation : {version_name}")
        print(f"     Modèle     : {model}")
        print(f"     Prompt     : {system_prompt[:60]}...")

        import ollama
        results = []

        for i, item in enumerate(dataset, 1):
            print(f"     [{i}/{len(dataset)}] {item['question'][:45]}...")
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
                answer = "Réponse simulée : " + item["question"]

            metrics = self.calculator.compute_all(
                question=item["question"],
                prediction=answer,
                reference=item.get("expected_answer", "")
            )
            results.append({**item, "answer": answer, **metrics})

        global_scores = self.gate.compute_global_score(results)
        score = global_scores["average_score"]
        color = self._get_color(score)
        print(f"     {color} Score : {score}")

        return {
            "version_name":  version_name,
            "model":         model,
            "system_prompt": system_prompt,
            **global_scores,
            "evaluated_at":  datetime.now().isoformat(),
        }

    def _get_color(self, score: float) -> str:
        if score >= 0.45:
            return "🟢 BON"
        elif score >= 0.30:
            return "🟡 MOYEN"
        else:
            return "🔴 MAUVAIS"

    def compare_prompts(self, dataset: list) -> dict:
        print("\n" + "=" * 55)
        print("  📝 COMPARAISON 1 — PROMPTS DIFFÉRENTS")
        print("  Même modèle, prompts différents")
        print("=" * 55)

        versions = [
            {
                "name":   "prompt_v1_simple",
                "prompt": "Tu es un assistant Django. Réponds en français.",
                "model":  "llama3.2:1b"
            },
            {
                "name":   "prompt_v2_expert",
                "prompt": "Tu es un expert Django senior. Donne des réponses précises et concises en français.",
                "model":  "llama3.2:1b"
            },
            {
                "name":   "prompt_v3_concis",
                "prompt": "Tu es un assistant Django. Réponds en UNE seule phrase courte. Maximum 20 mots.",
                "model":  "llama3.2:1b"
            },
        ]

        results = []
        for v in versions:
            result = self.evaluate_version(
                version_name=v["name"],
                system_prompt=v["prompt"],
                dataset=dataset,
                model=v["model"]
            )
            results.append(result)

        return self._display_results(results, title="PROMPTS")

    def compare_models(self, dataset: list) -> dict:
        print("\n" + "=" * 55)
        print("  🤖 COMPARAISON 2 — MODÈLES DIFFÉRENTS")
        print("  Même prompt, modèles différents")
        print("=" * 55)

        system_prompt = "Tu es un expert Django. Réponds en français de manière concise."

        versions = [
            {"name": "llama3.2:1b (léger)",  "model": "llama3.2:1b"},
            {"name": "llama3.2:3b (moyen)",  "model": "llama3.2:3b"},
            {"name": "mistral (puissant)",    "model": "mistral:latest"},
        ]

        results = []
        for v in versions:
            result = self.evaluate_version(
                version_name=v["name"],
                system_prompt=system_prompt,
                dataset=dataset,
                model=v["model"]
            )
            results.append(result)

        return self._display_results(results, title="MODÈLES")

    def _display_results(self, results: list, title: str) -> dict:
        print(f"\n  📊 Résultats — {title}")
        print(f"  {'─' * 51}")

        winner = max(results, key=lambda x: x["average_score"])

        for r in results:
            score = r["average_score"]
            color = self._get_color(score)
            flag  = " ← 🏆 GAGNANT" if r["version_name"] == winner["version_name"] else ""
            print(f"  {color} {r['version_name']:<30} → {score}{flag}")

        print(f"  {'─' * 51}")
        print(f"  🏆 Meilleur : {winner['version_name']}")
        print(f"  📌 Recommandation : Utiliser {winner['version_name']} en production")

        return {
            "results":      results,
            "winner":       winner["version_name"],
            "winner_score": winner["average_score"],
            "compared_at":  datetime.now().isoformat(),
        }

    def run_all(self, dataset_path: str = "dataset.json"):
        print("\n" + "🆚" * 27)
        print("  COMPARAISON COMPLÈTE — Topic 26 (Étudiant 2)")
        print("🆚" * 27)

        # Charger le dataset
        if os.path.exists(dataset_path):
            with open(dataset_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Gère les deux formats
            if isinstance(data, dict) and "dataset" in data:
                data = data["dataset"]
            print(f"\n📂 Dataset : {dataset_path} ({len(data)} questions)")
        else:
            print(f"⚠️  Dataset non trouvé : {dataset_path}")
            return

        prompt_results = self.compare_prompts(data)
        model_results  = self.compare_models(data)

        final_report = {
            "dataset":           dataset_path,
            "prompt_comparison": prompt_results,
            "model_comparison":  model_results,
            "generated_at":      datetime.now().isoformat(),
        }

        with open("comparison_results.json", "w", encoding="utf-8") as f:
            json.dump(final_report, f, indent=2, ensure_ascii=False)

        print("\n" + "=" * 55)
        print("  ✅ RAPPORT FINAL")
        print("=" * 55)
        print(f"  📂 Dataset         : {dataset_path}")
        print(f"  📝 Meilleur prompt : {prompt_results['winner']}")
        print(f"  🤖 Meilleur modèle : {model_results['winner']}")
        print(f"  💾 Rapport exporté → comparison_results.json")
        print("=" * 55)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Comparaison prompts et modèles")
    parser.add_argument("--dataset",   default="dataset.json",  help="Fichier dataset")
    parser.add_argument("--threshold", type=float, default=0.40, help="Seuil de score")
    args = parser.parse_args()

    comparator = VersionComparator(threshold=args.threshold)
    comparator.run_all(dataset_path=args.dataset)