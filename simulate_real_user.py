import urllib.request
import urllib.error
import time
import json
import random

URL = "http://127.0.0.1:8000/api/chat/"
HEADERS = {"Content-Type": "application/json"}

print("🚀 Démarrage de la simulation d'un VRAI utilisateur en temps réel...\n")

def send_question(question_text):
    print(f"👤 Utilisateur demande : '{question_text}'")
    try:
        # On prépare les données et la requête
        data = json.dumps({"prompt": question_text}).encode('utf-8')
        req = urllib.request.Request(URL, data=data, headers=HEADERS, method='POST')
        
        # On envoie la requête (qui sera interceptée par l'Étudiant 3)
        try:
            with urllib.request.urlopen(req) as response:
                headers = dict(response.headers)
        except urllib.error.HTTPError as e:
            # Même si c'est une erreur 404 (car l'API chat n'existe pas vraiment),
            # le middleware l'intercepte et renvoie les headers !
            headers = dict(e.headers)
            
        # Le middleware de l'étudiant 3 ajoute ces headers secrets dans la réponse !
        latence = headers.get("X-LLM-Latency-Ms", "N/A")
        drift = headers.get("X-LLM-Drift-Score", "N/A")
        
        print(f"   📊 [Monitor intercept] Latence: {latence}ms | Drift Score: {drift}")
        time.sleep(1) # Petite pause d'une seconde
        
    except urllib.error.URLError:
        print("   ❌ Erreur: Le serveur Django n'est pas lancé ! Lance 'python manage.py runserver' dans un autre terminal.")

print("--- PHASE 1 : Questions normales (Liées au dataset) ---")
# L'utilisateur pose des questions normales sur l'absentéisme / python
for i in range(3):
    send_question("Comment réduire l'absentéisme scolaire avec Python ?")

print("\n--- PHASE 2 : Le DRIFT ! (L'utilisateur pose des questions hors-sujet) ---")
# Soudainement, l'utilisateur pose des questions qui n'ont RIEN à voir
questions_drift = [
    "Quelle est la recette de la pizza margherita ?",
    "Comment réparer le moteur d'une voiture Peugeot ?",
    "Qui a gagné la coupe du monde en 1998 ?"
]

for q in questions_drift:
    send_question(q)

print("\n✅ Terminé ! Va regarder ton Dashboard Online, tu verras les alertes de Drift ! (N'oublie pas de rafraichir)")
