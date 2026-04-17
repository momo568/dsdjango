"""
train.py
Lance le RAG — charge le dataset comme base de connaissance
Lance ce fichier pour activer le RAG avant main.py
"""

from evaluation.rag import RAGRetriever

print("\n" + "🎓" * 20)
print("  CHARGEMENT RAG — Topic 26 (Étudiant 2)")
print("🎓" * 20)

# Charger le RAG avec le dataset
rag = RAGRetriever(dataset_path="dataset.json", top_k=2)

# Tester le RAG avec une question
print("\n🧪 Test du RAG :")
question = "C'est quoi Django ?"
context  = rag.build_context(question)
print(f"  Question : {question}")
print(f"  Contexte trouvé :\n{context[:200]}...")

print("\n✅ RAG prêt !")
print("   Lance : python main.py --model llama3:8b --limit 5")
print("   Ou    : python main.py --model llama3:8b --limit 5 --no-rag")
print("            pour comparer avec/sans RAG !")