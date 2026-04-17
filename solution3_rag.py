"""
solution3_rag.py
Solution 3 — RAG (Retrieval Augmented Generation)
Injecte le contexte pertinent du dataset dans le prompt
"""

import sys
import json
import random
import re

from evaluation.metrics import MetricsCalculator
from evaluation.release_gate import ReleaseGate


class SimpleRAG:
    """RAG hybride (TF-IDF par défaut, fallback sur mots)."""

    def __init__(self, dataset: list, top_k: int = 2):
        self.dataset = dataset
        self.top_k   = top_k
        self.use_sklearn = False
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            self.vectorizer = TfidfVectorizer()
            self.documents = [d.get("question", "") for d in self.dataset]
            if self.documents:
                self.tfidf_matrix = self.vectorizer.fit_transform(self.documents)
                self.use_sklearn = True
                print("  💡 TF-IDF initialisé avec succès pour la recherche sémantique !")
        except ImportError:
            print("  ⚠️ scikit-learn non trouvé. Mode fallback (mots en commun) activé.")

    def _similarity_fallback(self, text1: str, text2: str) -> float:
        import re
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / max(len(words1), len(words2))

    def get_context(self, question: str) -> str:
        if self.use_sklearn:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vec = self.vectorizer.transform([question])
            similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
            
            # Récupérer les indices des top_k meilleurs (si score > 0)
            top_indices = similarities.argsort()[-self.top_k:][::-1]
            scored = [self.dataset[i] for i in top_indices if similarities[i] > 0]
        else:
            scored = sorted(
                self.dataset,
                key=lambda d: self._similarity_fallback(question, d.get("question", "")),
                reverse=True
            )[:self.top_k]

        parts = []
        for i, doc in enumerate(scored, 1):
            parts.append(
                f"Document {i}:\n"
                f"Q: {doc.get('question', '')}\n"
                f"R: {doc.get('expected_answer', '')}"
            )
        return "\n\n".join(parts)

    def build_prompt(self, question: str) -> str:
        context = self.get_context(question)
        return (
            "Tu es un expert. Réponds en français de manière concise.\n\n"
            f"Utilise ces informations pour répondre :\n{context}\n\n"
            "Réponds directement en te basant sur ce contexte."
        )


def main(dataset_path="dataset.json", limit=5,
         model="llama3:8b", threshold=0.55):

    print("\n" + "🔵" * 27)
    print("  SOLUTION 3 — RAG")
    print("  Retrieval Augmented Generation")
    print("🔵" * 27)
    print(f"  📂 Dataset : {dataset_path}")
    print(f"  🤖 Modèle  : {model}")

    # Charger dataset
    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "dataset" in data:
        data = data["dataset"]

    full_data   = data.copy()
    if limit:
        data = random.sample(data, min(limit, len(data)))
    print(f"  🔢 Questions : {len(data)}")
    print(f"  📚 Base RAG  : {len(full_data)} documents")

    # Initialiser RAG
    rag        = SimpleRAG(dataset=full_data, top_k=2)
    calculator = MetricsCalculator()
    gate       = ReleaseGate(threshold=threshold)

    import ollama
    llm_results = []

    print("\n" + "=" * 55)
    print("  📤 Envoi des questions au LLM — mode RAG")
    print("=" * 55)

    for i, item in enumerate(data, 1):
        print(f"  [{i}/{len(data)}] {item['question'][:50]}...")

        system_prompt = rag.build_prompt(item["question"])

        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": item["question"]}
                ],
                options={"num_predict": 150}
            )
            answer = response.message.content
            status = "rag_mode"
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
    evaluated     = calculator.evaluate_all_results(llm_results)
    global_scores = gate.compute_global_score(evaluated)
    gate_result   = gate.apply_gate(global_scores)

    # Exporter
    gate.export_results(gate_result, "results_solution3.json")

    print(f"\n  🔵 RÉSULTAT SOLUTION 3 (RAG)")
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
    parser.add_argument("--model",     default="llama3:8b")
    parser.add_argument("--threshold", type=float, default=0.55)
    args = parser.parse_args()
    result = main(args.dataset, args.limit, args.model, args.threshold)
    sys.exit(0 if result["passed"] else 1)