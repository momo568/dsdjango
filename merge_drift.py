import json
import sys
import os

def main():
    if len(sys.argv) < 3:
        print("Usage: python merge_drift.py <fichier_drift.json> <dataset_cible.json>")
        print("Exemple: python merge_drift.py nouveau_dataset_drift.json dataset.json")
        sys.exit(1)

    drift_file = sys.argv[1]
    dataset_file = sys.argv[2]

    # 1. Lire le fichier généré par l'Étudiant 3
    if not os.path.exists(drift_file):
        print(f"❌ Erreur: Le fichier '{drift_file}' n'existe pas.")
        sys.exit(1)

    with open(drift_file, 'r', encoding='utf-8') as f:
        drift_data = json.load(f)

    # 2. Lire le dataset actuel de l'Étudiant 2
    with open(dataset_file, 'r', encoding='utf-8') as f:
        dataset = json.load(f)

    # Récupérer le dernier ID pour continuer l'incrémentation
    last_id = max([item.get('id', 0) for item in dataset]) if dataset else 0

    # 3. Ajouter automatiquement les nouvelles questions avec la réponse "Option B"
    added_count = 0
    for drift_item in drift_data:
        question = drift_item.get("prompt_a_traiter")
        
        # Petit hack pour récupérer la vraie question si elle était stockée dans la DB
        # (Dans la démo, on utilise une phrase générique, mais ici on va la formater)
        if question:
            last_id += 1
            dataset.append({
                "id": last_id,
                "question": question,
                "expected_answer": "Désolé, je suis un assistant spécialisé dans l'absentéisme scolaire, je ne peux pas répondre à cette question."
            })
            added_count += 1

    # 4. Sauvegarder le dataset mis à jour
    with open(dataset_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    print("\n" + "="*50)
    print(" 🔄 FUSION DU DRIFT RÉUSSIE (BOUCLE AUTOMATISÉE)")
    print("="*50)
    print(f" ✅ {added_count} nouvelles questions hors-sujet ont été ajoutées.")
    print(f" 🎯 Réponse attendue configurée sur : 'Désolé, je suis un assistant...'")
    print(f" 💾 Fichier mis à jour : {dataset_file}")
    print("\n 👉 Prochaine étape : relance 'python main.py --dataset " + dataset_file + "'")

if __name__ == "__main__":
    main()
