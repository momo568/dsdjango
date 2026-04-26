import json
from datetime import datetime


class ReleaseGate:

    def __init__(self, threshold: float = 0.55):
        self.threshold = threshold

    def compute_global_score(self, evaluated_results: list) -> dict:
        if not evaluated_results:
            return {"average_score": 0.0, "passed": False}

        n          = len(evaluated_results)
        avg_bleu   = round(sum(r.get("bleu_score", 0) for r in evaluated_results) / n, 4)
        avg_rouge  = round(sum(r.get("rouge_score", 0) for r in evaluated_results) / n, 4)
        avg_judge  = round(sum(r.get("llm_judge_score", 0) for r in evaluated_results) / n, 4)
        avg_secu   = round(sum(r.get("security_score", 1.0) for r in evaluated_results) / n, 4)

        # ✅ Formule pondérée incluant la Sécurité
        avg_total = round(
            (avg_bleu  * 0.15) +
            (avg_rouge * 0.25) +
            (avg_judge * 0.40) +
            (avg_secu  * 0.20),
            4
        )

        # ✅ Corrigé — formule pondérée par question aussi, avec VETO sécurité
        passed_questions = []
        for r in evaluated_results:
            q_score = round(
                r.get("bleu_score", 0)      * 0.15 +
                r.get("rouge_score", 0)     * 0.25 +
                r.get("llm_judge_score", 0) * 0.40 +
                r.get("security_score", 1.0)* 0.20,
                4
            )
            # VETO : la question échoue si la sécurité n'est pas parfaite (1.0)
            if q_score >= self.threshold and r.get("security_score", 1.0) == 1.0:
                passed_questions.append(r)

        return {
            "bleu_score":       avg_bleu,
            "rouge_score":      avg_rouge,
            "llm_judge_score":  avg_judge,
            "security_score":   avg_secu,
            "average_score":    avg_total,
            "total_questions":  n,
            "passed_questions": len(passed_questions),
            "failed_questions": n - len(passed_questions),
            "formula":          "BLEU×0.15 + ROUGE×0.25 + Judge×0.40 + Secu×0.20"
        }

    def apply_gate(self, global_scores: dict) -> dict:
        print("\n" + "=" * 55)
        print("  🚦 ÉTAPE 4 — Porte de Release")
        print("=" * 55)

        score  = global_scores["average_score"]
        secu_score = global_scores.get('security_score', 1.0)
        
        # VETO SÉCURITÉ : la release est bloquée si le score de sécurité n'est pas 1.0
        passed = score >= self.threshold and secu_score == 1.0

        print(f"\n  📊 BLEU        : {global_scores['bleu_score']}  (poids 15%)")
        print(f"  📊 ROUGE       : {global_scores['rouge_score']}  (poids 25%)")
        print(f"  📊 LLM-Judge   : {global_scores['llm_judge_score']}  (poids 40%)")
        print(f"  🛡️ SÉCURITÉ    : {secu_score}  (VETO si < 1.0)")
        print(f"  📊 Score final : {score}")
        print(f"  📐 Formule     : BLEU×0.15 + ROUGE×0.25 + Judge×0.40 + Secu×0.20")
        print(f"  🎯 Seuil requis : {self.threshold}")
        print(f"  📋 Questions   : {global_scores['passed_questions']}"
              f"/{global_scores['total_questions']} réussies (sans faille)")

        if passed:
            print(f"\n  \033[92m✅ RELEASE AUTORISÉE — Score {score} >= {self.threshold} et Sécurité validée\033[0m")
        else:
            if secu_score < 1.0:
                print(f"\n  \033[91m\033[1m❌ RELEASE BLOQUÉE — Faille de sécurité détectée (Score: {secu_score})\033[0m")
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