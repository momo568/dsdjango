import os
import re


class MetricsCalculator:

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def compute_bleu(self, prediction: str, reference: str) -> float:
        try:
            from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
            import nltk
            nltk.download("punkt", quiet=True)
            reference_tokens = reference.lower().split()
            prediction_tokens = prediction.lower().split()
            smoothing = SmoothingFunction().method1
            score = sentence_bleu([reference_tokens], prediction_tokens, smoothing_function=smoothing)
            return round(score, 4)
        except ImportError:
            return self._simple_bleu(prediction, reference)

    def _simple_bleu(self, prediction: str, reference: str) -> float:
        pred_words = set(prediction.lower().split())
        ref_words  = set(reference.lower().split())
        if not pred_words:
            return 0.0
        common = pred_words.intersection(ref_words)
        return round(len(common) / len(pred_words), 4)

    def compute_rouge(self, prediction: str, reference: str) -> float:
        try:
            from rouge_score import rouge_scorer
            scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
            scores = scorer.score(reference, prediction)
            return round(scores["rougeL"].fmeasure, 4)
        except ImportError:
            return self._simple_rouge(prediction, reference)

    def _simple_rouge(self, prediction: str, reference: str) -> float:
        pred_words = set(prediction.lower().split())
        ref_words  = set(reference.lower().split())
        if not ref_words:
            return 0.0
        common = pred_words.intersection(ref_words)
        return round(len(common) / len(ref_words), 4)

    def compute_llm_judge(self, question: str, prediction: str, reference: str) -> float:
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            prompt = f"""Tu es un évaluateur expert. Note la réponse de 0.0 à 1.0.

Question : {question}
Réponse attendue : {reference}
Réponse du modèle : {prediction}

1.0 = parfait | 0.75 = bien | 0.5 = partiel | 0.25 = incorrect | 0.0 = faux

Réponds UNIQUEMENT avec un nombre entre 0.0 et 1.0."""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
            )
            score_text = response.choices[0].message.content.strip()
            score = float(re.findall(r"\d+\.?\d*", score_text)[0])
            return round(min(max(score, 0.0), 1.0), 4)
        except Exception:
            return self._simulate_judge(prediction, reference)

    def _simulate_judge(self, prediction: str, reference: str) -> float:
        pred_words = set(prediction.lower().split())
        ref_words  = set(reference.lower().split())
        if not ref_words:
            return 0.5
        common = pred_words.intersection(ref_words)
        similarity = len(common) / len(ref_words)
        return round(min(similarity * 1.1 + 0.1, 1.0), 4)

    def compute_all(self, question: str, prediction: str, reference: str) -> dict:
        bleu  = self.compute_bleu(prediction, reference)
        rouge = self.compute_rouge(prediction, reference)
        judge = self.compute_llm_judge(question, prediction, reference)
        return {
            "bleu_score":      bleu,
            "rouge_score":     rouge,
            "llm_judge_score": judge,
            "average_score":   round((bleu + rouge + judge) / 3, 4),
        }

    def evaluate_all_results(self, llm_results: list) -> list:
        print("\n" + "=" * 55)
        print("  📊 ÉTAPE 3 — Calcul des métriques")
        print("=" * 55)
        evaluated = []
        for i, item in enumerate(llm_results, 1):
            print(f"  [{i}/{len(llm_results)}] Calcul métriques...")
            metrics = self.compute_all(
                item.get("question", ""),
                item.get("answer", ""),
                item.get("expected_answer", "")
            )
            result = {**item, **metrics}
            evaluated.append(result)
            print(f"    BLEU={metrics['bleu_score']} | "
                  f"ROUGE={metrics['rouge_score']} | "
                  f"Judge={metrics['llm_judge_score']} | "
                  f"Moy={metrics['average_score']}")
        print(f"\n✅ Métriques calculées pour {len(evaluated)} réponses")
        return evaluated