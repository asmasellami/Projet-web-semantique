# Assurance et sinistres — application et NLP multilingue

Application Django, ontologie OWL et serveur Apache Jena Fuseki. Les données métier sont dans un graphe RDF ; SQLite sert aux tables internes de Django.

## Installation locale Windows

1. Java compatible avec Fuseki (environnement vérifié : Java 24, Fuseki 5.6.0), Python 3.13 et Git.
2. Dans le dépôt : `python -m venv .venv`, puis `.\.venv\Scripts\python -m pip install -r requirements.txt`.
3. Pour reproduire l'ancien moteur français : `.\.venv\Scripts\python -m spacy download fr_core_news_sm`.
4. Lancer Fuseki, créer un dataset persistant TDB2 nommé `assurance` et importer une fois `assurance_inferee.owl` fourni séparément par l'équipe. Le dépôt n'inclut pas cette référence locale. L'original doit rester sauvegardé.
5. Définir `$env:FUSEKI_URL = 'http://127.0.0.1:3030/assurance'` dans le terminal Django.
6. `.\.venv\Scripts\python manage.py migrate`, puis `.\.venv\Scripts\python manage.py runserver`.

Application : http://127.0.0.1:8000/ ; assistant multilingue : http://127.0.0.1:8000/assistant/ ; ancien moteur français : http://127.0.0.1:8000/question/ ; base Fuseki : http://127.0.0.1:3030/.

## Conversation et exploration

La version actuelle conserve un historique et une sélection visible par session Django. Commencer par les suggestions d'exploration, sélectionner un résultat, puis poser des questions de suivi. Les suggestions évoluent avec les résultats et la sélection. « Nouvelle conversation » réinitialise l'historique et le contexte. Les onglets d'une même session partagent la conversation ; les actions périmées sont refusées.

La version de conversation comprend 23 contrats de requêtes, un classifieur enrichi et des règles explicites de relations/contexte. Pour reproduire le modèle actuel : `python ml/train_conversation.py`, puis redémarrer Django. Le modèle sélectionné est `ml/artifacts/conversation-tfidf.joblib`. Voir `ml/CONVERSATION_RESULTS.md` pour les fonctionnalités, les deux critiques du plan, les résultats et les limites.

## Modèle local

Les poids/modèles générés sont ignorés par Git. Il faut soit les entraîner avec les commandes suivantes, soit copier le dossier `ml/artifacts/` depuis la machine de réalisation. Aucun envoi vers une API LLM n'est effectué lors des questions.

Baseline entraînable sans transformers :

```powershell
python ml/build_dataset.py
python ml/train.py
```

Comparaison complète dans un environnement ML séparé (versions vérifiées enregistrées dans `ml/requirements-lock.txt`) :

```powershell
python -m pip install setfit sentence-transformers
python ml/train.py --transformers
python ml/blend.py
```

Le premier chargement de MiniLM télécharge le modèle. L'inférence utilise ensuite les fichiers locaux. Le serveur qui utilise SetFit/MiniLM doit être lancé avec l'environnement contenant ces bibliothèques. L'environnement baseline ne nécessite que les dépendances de `requirements.txt`. `blend.py` est l'expérience complémentaire de combinaison, documentée dans le rapport ; elle n'est pas nécessaire pour utiliser le modèle retenu.

L'entraînement compare TF-IDF + régression logistique, MiniLM gelé + régression logistique et MiniLM affiné avec SetFit. Le choix du moteur et des seuils utilise uniquement la validation ; les résultats de test sont ensuite enregistrés. `ml/artifacts/selected.json` indique le modèle choisi. Le modèle est chargé une fois par processus ; redémarrer Django après changement du modèle.

## Capacités et limites

Les dix familles initiales sont complétées par découverte, recherches inverses véhicule/contrat, fiche sinistre et navigation client/compagnie/contrat. Le détail des 23 contrats est dans `app/multilingual/contracts.py`.

Français, anglais et Arabizi tunisien expérimental. Corpus de départ rédigé avec assistance IA ; revue par locuteurs tunisiens toujours nécessaire. Les scores internes ne prouvent pas une compréhension générale du dialecte. Le corpus et ses groupes sont documentés dans `ml/data/README.md`.

Les intentions, entités, filtres, chemin de relations et SPARQL exécuté sont visibles. Les résultats sont des tableaux. Les entités sont retrouvées dans le graphe à chaque question. Les identifiants inconnus/ambigus demandent une précision. Le comptage, l'existence, les comparaisons et les écritures par NLP ne font pas partie de cette version.

Les filtres des sinistres comprennent lieu, statut, type et dates explicites ; les montants sont filtrables pour l'indemnisation. Les formulations non reconnues peuvent être refusées. Les inférences HermiT sont celles de l'export OWL ; elles ne sont pas recalculées automatiquement après CRUD.

## Tests et évaluation

```powershell
$env:ASSURANCE_OWL = 'CHEMIN_COMPLET\assurance_inferee.owl'
python manage.py test app
python ml/evaluate_answers.py
```

La suite Django utilise `assurance_member3_test`, isolé de `assurance`. Elle remet le dataset de test à zéro. Le benchmark de réponses utilise des SELECT et vérifie que le nombre de triplets du dataset choisi ne change pas ; utiliser le jeu de référence pour comparer les réponses attendues.

`ml/reports/classification.json` : jeux/scores/seuils/choix du modèle ; `ml/reports/answers.json` : réponses exactes à un challenge indépendant. Voir le rapport de réalisation pour les résultats et les limites mesurées.
