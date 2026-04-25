# 📖 L'Histoire du Code — Comment tout est connecté (Oumaima & l'Équipe)

Ce fichier est différent du premier. Ici, nous n'allons pas parler de théorie, mais de **l'histoire de ton code**. C'est la "carte du trésor" qui montre comment tous les fichiers Python discutent entre eux, de la question posée jusqu'au déploiement final.

---

## 🗺️ 1. La Carte des Rôles (Qui fait quoi ?)

Imagine ton projet comme une usine automobile. Chacun a son poste, et la voiture avance sur le tapis roulant d'un fichier à l'autre.

* **Le Fournisseur (Étudiant 1) :** Il amène les pièces détachées. C'est le fichier `dataset.json` (et ton `dataset_hack.json`). Il contient les questions.
* **Le Moteur (Mahmoud - Étudiant 3) :** Ses fichiers sont `llm_caller.py` et `rag.py`. Il prend la question, cherche dans les cours, et fait parler l'IA.
* **Le Contrôle Qualité (Toi, Oumaima - Étudiant 2) :** Tes fichiers sont `main.py`, `metrics.py` et `release_gate.py`. Tu récupères la voiture (la réponse de l'IA), tu la fais passer au crash-test (les 4 métriques), et tu décides si elle a le droit de sortir de l'usine (VETO).
* **Les Vendeurs (Étudiants 4 et 5) :** Ils lisent le rapport que tu as écrit (`eval_results.json`) pour afficher de beaux graphiques (Dashboard) et mettre le système en ligne (Déploiement).

---

## 🚀 2. Le Voyage d'une Question (L'entonnoir du Code)

Que se passe-t-il exactement dans l'ordinateur quand tu lances `python main.py` ? Voici l'histoire étape par étape :

### Étape 1 : Le Chef d'Orchestre se réveille (`main.py`)
C'est ton fichier principal. C'est lui qui lance l'usine. Il lit une question du dataset, par exemple : *"C'est quoi un modèle dans Django ?"*.

### Étape 2 : L'Appel à Mahmoud (`llm_caller.py` & `rag.py`)
Ton fichier `main.py` appelle le code de Mahmoud et lui donne la question.
1. Le code de Mahmoud utilise `rag.py` pour fouiller très vite dans tous les cours de Django et extraire le bon paragraphe.
2. Le code de Mahmoud donne la question ET le paragraphe à **Ollama** (L'IA).
3. Ollama écrit sa réponse : *"Un modèle Django représente une table dans la base de données"*.
4. Le fichier de Mahmoud **te renvoie** cette réponse. Le travail de Mahmoud est terminé.

### Étape 3 : Le Grand Tribunal (`metrics.py`)
Maintenant, ton `main.py` possède la réponse générée. Il l'envoie à ton tribunal, le fichier `metrics.py`. C'est là que la réponse se fait torturer par tes 4 algorithmes :
* `compute_bleu()` vérifie l'orthographe (NLTK).
* `compute_rouge()` vérifie l'ordre des mots (Rouge-Score).
* `compute_llm_judge()` demande à un autre LLM si la réponse est intelligente.
* `compute_security_score()` passe la réponse au détecteur de mensonges (Blacklist + IA de cybersécurité).

### Étape 4 : Le Videur de la Boîte de Nuit (`release_gate.py`)
Toutes les notes de l'étape 3 sont envoyées au fichier `release_gate.py`. 
Ce fichier fait la moyenne de tout. Puis, il regarde son règlement très strict :
* *"Est-ce que la moyenne est au-dessus de 0.55 ?"*
* *"Est-ce que Oumaima a mis 1.0 en Sécurité ?"*
Si tout est parfait, le fichier écrit fièrement le mot **"DEPLOY"**. Sinon, il claque la porte et écrit **"BLOCK"**.

### Étape 5 : L'Export Final (`eval_results.json`)
La décision du videur est sauvegardée dans un fichier texte qui s'appelle `eval_results.json`. Ton travail d'Évaluatrice est terminé ! L'usine s'arrête.

---

## 🔬 3. Tes Outils de "Laboratoire" Secrets

En plus de cette usine officielle, tu as programmé des outils scientifiques (des laboratoires privés) pour faire des expériences. Ce sont tes autres fichiers :

### 🧪 Les 5 Solutions (`solution1_no_rag.py` à `solution5_consensus.py`)
C'est là que tu as testé différentes configurations d'usine. Tu as essayé de faire l'usine sans le RAG de Mahmoud (Solution 1), ou avec une IA qui se corrige elle-même (Solution 4). Tu as prouvé avec tes propres notes que c'est la Solution 3 (le RAG) qui donne le meilleur `eval_results.json`.

### ⚖️ L'A/B Testing (`version_comparator.py`)
C'est ton chef-d'œuvre de Lead Tech. Ce fichier lance toute l'usine plusieurs fois d'affilée en changeant un seul paramètre (le modèle Llama vs Mistral, ou le prompt). À la fin, il génère le fichier `comparison_results.json` pour dire à l'entreprise quelle configuration utiliser pour gagner le plus d'argent.

### 🛡️ Le Stand de Tir (`test_security.py`)
C'est le fichier que tu as créé pour prouver que ta métrique de sécurité n'est pas cassable. Il envoie exprès des virus, des insultes et des mots de passe à ton système pour montrer au jury que ton code `metrics.py` les bloque tous (Score = 0.0) et que ton VETO fonctionne !

---
**💡 Résumé des relations du code :** 
`dataset.json` (Questions) ➡️ `llm_caller.py` (Mahmoud génère) ➡️ `metrics.py` (Oumaima note) ➡️ `release_gate.py` (Oumaima décide) ➡️ `eval_results.json` (Résultat final).
