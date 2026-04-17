"""
evaluation/rag.py
Étudiant 2 — RAG (Retrieval Augmented Generation)
Cherche le contexte le plus pertinent dans le dataset
et l'injecte dans le prompt avant d'appeler le LLM
"""

import json
import os
import re


class RAGRetriever:
    """
    Retriever simple basé sur la similarité des mots.
    Cherche les questions/réponses les plus proches
    dans le dataset et les injecte comme contexte.
    """

    def __init__(self, dataset_path: str = "dataset.json", top_k: int = 2):
        self.top_k    = top_k
        self.dataset  = []
        self.load_dataset(dataset_path)

    # ──────────────────────────────────────────────────
    # Charger le dataset
    # ──────────────────────────────────────────────────
    def load_dataset(self, dataset_path: str):
        if os.path.exists(dataset_path):
            with open(dataset_path, "r", encoding="utf-8") as f:
                self.dataset = json.load(f)
            print(f"📚 RAG chargé : {len(self.dataset)} documents")
        else:
            print("⚠️  Dataset non trouvé pour RAG")

    # ──────────────────────────────────────────────────
    # Calculer la similarité entre deux textes
    # ──────────────────────────────────────────────────
    def _similarity(self, text1: str, text2: str) -> float:
        """Similarité simple basée sur les mots en commun."""
        words1 = set(re.findall(r'\w+', text1.lower()))
        words2 = set(re.findall(r'\w+', text2.lower()))
        if not words1 or not words2:
            return 0.0
        common = words1.intersection(words2)
        return len(common) / max(len(words1), len(words2))

    # ──────────────────────────────────────────────────
    # Chercher les documents les plus pertinents
    # ──────────────────────────────────────────────────
    def retrieve(self, question: str) -> list:
        """
        Cherche les top_k documents les plus similaires
        à la question posée.
        """
        if not self.dataset:
            return []

        # Calculer la similarité avec chaque document
        scored = []
        for doc in self.dataset:
            sim_question = self._similarity(question, doc.get("question", ""))
            sim_answer   = self._similarity(question, doc.get("expected_answer", ""))
            score        = max(sim_question, sim_answer)
            scored.append((score, doc))

        # Trier par score décroissant
        scored.sort(key=lambda x: x[0], reverse=True)

        # Retourner les top_k meilleurs
        return [doc for _, doc in scored[:self.top_k]]

    # ──────────────────────────────────────────────────
    # Construire le contexte RAG
    # ──────────────────────────────────────────────────
    def build_context(self, question: str) -> str:
        """
        Construit le contexte à injecter dans le prompt.
        """
        docs = self.retrieve(question)
        if not docs:
            return ""

        context_parts = []
        for i, doc in enumerate(docs, 1):
            context_parts.append(
                f"Document {i}:\n"
                f"Q: {doc.get('question', '')}\n"
                f"R: {doc.get('expected_answer', '')}"
            )

        return "\n\n".join(context_parts)

    # ──────────────────────────────────────────────────
    # Construire le prompt complet avec contexte
    # ──────────────────────────────────────────────────
    def build_rag_prompt(self, question: str, base_prompt: str) -> str:
        """
        Injecte le contexte RAG dans le prompt système.
        """
        context = self.build_context(question)
        if not context:
            return base_prompt

        return (
            f"{base_prompt}\n\n"
            f"Utilise ces informations pertinentes pour répondre :\n"
            f"{context}\n\n"
            f"Réponds de manière concise en te basant sur ce contexte."
        )