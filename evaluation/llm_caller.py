"""
evaluation/llm_caller.py
Étudiant 2 — LLM Caller avec RAG réel
"""

import json
import os
import time
import traceback
from datetime import datetime
class LLMCaller:

    def __init__(self, model: str = "llama3.2:1b", use_rag: bool = True, dataset_path: str = "dataset.json"):
        self.model    = model
        self.use_rag  = use_rag
        self.rag      = None

        # Charger le RAG si activé
        if self.use_rag:
            from evaluation.rag import RAGRetriever
            self.rag = RAGRetriever(dataset_path=dataset_path, top_k=2)
            print(f"🔍 RAG activé → top_k=2")
        else:
            print(f"🔍 RAG désactivé")

    def call_llm(self, question: str) -> dict:
        try:
            import ollama
            start_time = time.time()

            # ── Prompt de base ──────────────────────────────
            base_prompt = (
                "Tu es un expert Django. "
                "Réponds en français de manière concise et précise."
            )

            # ── RAG : injecter le contexte ──────────────────
            if self.use_rag and self.rag:
                system_content = self.rag.build_rag_prompt(question, base_prompt)
                mode = "rag_mode"
            else:
                system_content = base_prompt
                mode = "raw_mode"

            # ── Appel LLM ───────────────────────────────────
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_content},
                    {"role": "user",   "content": question}
                ],
                options={"num_predict": 150}
            )

            latency_ms = round((time.time() - start_time) * 1000, 2)
            answer     = response.message.content

            return {
                "question":    question,
                "answer":      answer,
                "model":       self.model,
                "mode":        mode,
                "latency_ms":  latency_ms,
                "tokens_used": len(answer.split()),
                "status":      "success",
                "timestamp":   datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"⚠️  Mode simulation activé")
            print(f"❌ Erreur : {e}")
            traceback.print_exc()
            return self._simulate_response(question)

    def _simulate_response(self, question: str) -> dict:
        simulated = {
            "Django": "Django est un framework web Python de haut niveau.",
            "ORM":    "L'ORM Django permet d'interagir avec la base de données en Python.",
            "ASGI":   "ASGI est l'interface asynchrone de Django.",
        }
        answer = "Réponse simulée pour : " + question
        for keyword, resp in simulated.items():
            if keyword.lower() in question.lower():
                answer = resp
                break
        return {
            "question":    question,
            "answer":      answer,
            "model":       "simulation",
            "mode":        "simulation",
            "latency_ms":  150.0,
            "tokens_used": 50,
            "status":      "simulated",
            "timestamp":   datetime.now().isoformat(),
        }

    def train_now(self, dataset_path: str = "dataset.json"):
        """Recharge le RAG avec le nouveau dataset."""
        print("\n" + "🎓" * 20)
        print("  CHARGEMENT RAG — Topic 26")
        print("🎓" * 20)

        if os.path.exists(dataset_path):
            from evaluation.rag import RAGRetriever
            self.rag = RAGRetriever(dataset_path=dataset_path, top_k=2)
            print(f"✅ RAG rechargé avec succès !")
        else:
            print("❌ Dataset non trouvé !")

    def process_dataset(self, dataset_path: str = "dataset.json") -> list:
        print("=" * 55)
        print("  📤 ÉTAPE 2 — Envoi des questions au LLM")
        print("=" * 55)

        if os.path.exists(dataset_path):
            with open(dataset_path, "r", encoding="utf-8") as f:
                dataset = json.load(f)
        else:
            print("⚠️  Dataset non trouvé — démo activée")
            dataset = [
                {"question": "C'est quoi Django ?",
                 "expected_answer": "Django est un framework Python."},
            ]

        print(f"📂 Dataset chargé : {len(dataset)} questions")
        results = []
        for i, item in enumerate(dataset, 1):
            print(f"  [{i}/{len(dataset)}] {item['question'][:50]}...")
            result = self.call_llm(item["question"])
            result["expected_answer"] = item.get("expected_answer", "")
            results.append(result)
        print(f"\n✅ {len(results)} réponses récupérées")
        return results