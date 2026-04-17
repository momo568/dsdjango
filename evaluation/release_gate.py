import json
from datetime import datetime


class ReleaseGate:

    def __init__(self, threshold: float = 0.40):
        self.threshold = threshold

    def compute_global_score(self, evaluated_results: list) -> dict:
        if not evaluated_results:
            return {"average_score": 0.0, "passed": False}

        n          = len(evaluated_results)
        avg_bleu   = round(sum(r.get("bleu_score", 0) for r in evaluated_results) / n, 4)
        avg_rouge  = round(sum(r.get("rouge_score", 0) for r in evaluated_results) / n, 4)
        avg_judge  = round(sum(r.get("llm_judge_score", 0) for r in evaluated_results) / n, 4)

        # ✅ Formule pondérée — LLM-Judge est plus fiable
        avg_total = round(
            (avg_bleu  * 0.2) +
            (avg_rouge * 0.3) +
            (avg_judge * 0.5),
            4
        )

        # ✅ Corrigé — formule pondérée par question aussi
        passed_questions = [
            r for r in evaluated_results
            if round(
                r.get("bleu_score", 0)      * 0.2 +
                r.get("rouge_score", 0)     * 0.3 +
                r.get("llm_judge_score", 0) * 0.5,
                4
            ) >= self.threshold
        ]

        return {
            "bleu_score":       avg_bleu,
            "rouge_score":      avg_rouge,
            "llm_judge_score":  avg_judge,
            "average_score":    avg_total,
            "total_questions":  n,
            "passed_questions": len(passed_questions),
            "failed_questions": n - len(passed_questions),
            "formula":          "BLEU×0.2 + ROUGE×0.3 + Judge×0.5"
        }

    def apply_gate(self, global_scores: dict) -> dict:
        print("\n" + "=" * 55)
        print("  🚦 ÉTAPE 4 — Porte de Release")
        print("=" * 55)

        score  = global_scores["average_score"]
        passed = score >= self.threshold

        print(f"\n  📊 BLEU        : {global_scores['bleu_score']}  (poids 20%)")
        print(f"  📊 ROUGE       : {global_scores['rouge_score']}  (poids 30%)")
        print(f"  📊 LLM-Judge   : {global_scores['llm_judge_score']}  (poids 50%)")
        print(f"  📊 Score final : {score}")
        print(f"  📐 Formule     : BLEU×0.2 + ROUGE×0.3 + Judge×0.5")
        print(f"  🎯 Seuil requis : {self.threshold}")
        print(f"  📋 Questions   : {global_scores['passed_questions']}"
              f"/{global_scores['total_questions']} réussies")

        if passed:
            print(f"\n  \033[92m✅ RELEASE AUTORISÉE — Score {score} >= {self.threshold}\033[0m")
        else:
            print(f"\n  \033[91m\033[1m❌ RELEASE BLOQUÉE — Score {score} < {self.threshold}\033[0m")

        return {
            **global_scores,
            "passed":       passed,
            "decision":     "DEPLOY" if passed else "BLOCK",
            "threshold":    self.threshold,
            "evaluated_at": datetime.utcnow().isoformat(),
        }

    def export_results(self, gate_result: dict, output_path: str = "eval_results.json"):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(gate_result, f, indent=2, ensure_ascii=False)
        print(f"\n  💾 Résultats exportés → {output_path}")
        print(f"  → Étudiant 4 : dashboard")
        print(f"  → Étudiant 5 : déploiement")
        print("=" * 55)