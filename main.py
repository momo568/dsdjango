import argparse
import sys
import json
import random
import os

from dotenv import load_dotenv
load_dotenv()

from evaluation.llm_caller import LLMCaller
from evaluation.metrics import MetricsCalculator
from evaluation.release_gate import ReleaseGate


def load_dataset(path: str, limit: int = None) -> list:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # ✅ Gère les deux formats
    if isinstance(data, dict) and "dataset" in data:
        data = data["dataset"]

    if limit:
        data = random.sample(data, min(limit, len(data)))
        print(f"🎲 Échantillon aléatoire : {len(data)} questions")
    return data


def main():
    parser = argparse.ArgumentParser(description="Pipeline LLM — Étudiant 2")
    parser.add_argument("--dataset",   default="dataset.json",      help="Fichier dataset")
    parser.add_argument("--output",    default="eval_results.json", help="Fichier de sortie")
    parser.add_argument("--threshold", type=float, default=0.55,    help="Seuil de release")
    parser.add_argument("--limit",     type=int,   default=None,    help="Nombre de questions")
    parser.add_argument("--model",     default="llama3.2:1b",       help="Modèle Ollama")
    parser.add_argument("--no-rag",    action="store_true",         help="Désactiver le RAG")
    args = parser.parse_args()

    # Vérifier si RAG activé
    use_rag = not args.no_rag
    trained = os.path.exists("brain_memory.txt")

    print("\n" + "🔬" * 27)
    print("  PIPELINE D'ÉVALUATION LLM — Topic 26 (Étudiant 2)")
    print("🔬" * 27)
    print(f"  📂 Dataset   : {args.dataset}")
    print(f"  🤖 Modèle    : {args.model}")
    print(f"  🎯 Seuil     : {args.threshold}")
    print(f"  🧠 Mémoire   : {'✅ Entraîné' if trained else '❌ Non entraîné'}")
    print(f"  🔍 RAG       : {'✅ Activé' if use_rag else '❌ Désactivé'}")
    if args.limit:
        print(f"  🔢 Limite    : {args.limit} questions")

    # ── ÉTAPE 2 ─────────────────────────────────────────
    print("\n" + "=" * 55)
    print("  📤 ÉTAPE 2 — Envoi des questions au LLM")
    print("=" * 55)

    dataset     = load_dataset(args.dataset, limit=args.limit)
    caller      = LLMCaller(model=args.model, use_rag=use_rag)
    llm_results = []

    for i, item in enumerate(dataset, 1):
        print(f"  [{i}/{len(dataset)}] {item['question'][:50]}...")
        result = caller.call_llm(item["question"])
        result["expected_answer"] = item.get("expected_answer", "")
        llm_results.append(result)

    print(f"\n✅ {len(llm_results)} réponses récupérées")

    # ── ÉTAPE 3 ─────────────────────────────────────────
    calculator        = MetricsCalculator()
    evaluated_results = calculator.evaluate_all_results(llm_results)

    # ── ÉTAPE 4 ─────────────────────────────────────────
    gate          = ReleaseGate(threshold=args.threshold)
    global_scores = gate.compute_global_score(evaluated_results)
    gate_result   = gate.apply_gate(global_scores)

    # ── ÉTAPE 5 ─────────────────────────────────────────
    gate.export_results(gate_result, output_path=args.output)

    # ── Résumé final ─────────────────────────────────────
    print(f"\n  🔍 Mode RAG    : {'Activé ✅' if use_rag else 'Désactivé ❌'}")
    print(f"  🎯 Décision    : {gate_result['decision']}")

    if gate_result["passed"]:
        print("  🟢 RELEASE AUTORISÉE — modèle prêt pour la production !")
    else:
        print("  🔴 RELEASE BLOQUÉE — active le RAG pour améliorer !")
        if not use_rag:
            print("  💡 Conseil : lance sans --no-rag pour activer le RAG !")

    sys.exit(0 if gate_result["passed"] else 1)


if __name__ == "__main__":
    main()