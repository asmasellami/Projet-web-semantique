# Membre 3 — Guide de soutenance

## 1. Ce qu'il faut savoir dire en une minute

« J'ai géré les classes **Acteur** (assurés, experts, bénéficiaires, compagnies) et **BienAssure** (véhicules, logements,
personnes assurées) : pages avec lecture, recherche, filtres et CRUD en SPARQL, et le **module NLP** qui transforme une
question en français en requête SPARQL avec **spaCy** (règles d'intention + templates), sans LLM. »

Outils à citer : **spaCy** (TALN), Django, SPARQLWrapper, Apache Jena Fuseki, Protégé / HermiT (ontologie, faite en amont).

## 2. Préparation avant la soutenance

1. Lancer Fuseki (`fuseki-server.bat`) puis Django (`python manage.py runserver`).
2. Vérifier `http://localhost:3030` (dataset `assurance`) et `http://127.0.0.1:8000/`.
3. Facultatif pour la démo « STAR » : créer la compagnie (voir scénario D).

## 3. Scénarios de démonstration

**A. Assurés (`/assures/`)** — liste de 4 assurés avec biens, contrats, compagnies ; filtre « compagnie = MedAssur » → Youssef ;
recherche « trabelsi » → Salma ; le badge rouge « Doublon de Client CRM 4471 » illustre la clé OWL `cin` (`HasKey`).
Bouton « + Nouvel assuré » → formulaire `Assure` ; essayer un CIN existant (`08123456`) → refus ; bonus-malus `4` → refus
(facette OWL 0,5–3,5) ; créer « Karim Zouari », retour automatique sur `/assures/`.

**B. Biens (`/biens/`)** — filtrer par type / propriétaire / valeur ; créer un véhicule avec immatriculation `123 TU 4567`
→ refusé (clé OWL) ; puissance fiscale `60` → refusé ; créer un logement : liste « Appartement, Duplex, Studio, Villa »
(l'énumération de l'ontologie) ; choisir propriétaire et contrat couvrant ; montrer ensuite dans Fuseki
(`SELECT * WHERE { :Assure_X :estProprietaireDe ?b }`) que l'**inverse** a été écrit.

**C. NLP (`/question/`)**

| Question | Résultat attendu |
|---|---|
| Quels sont les biens assurés de Ahmed ? | Kia Picanto (123 TU 4567) + Personne assurée CNAM (via le contrat santé) |
| Montre les biens de Salma. | Logement Ariana |
| Liste les biens assurés appartenant à Ahmed. | idem, intention *biens_assure* |
| Quels sont les assurés de AssurTunis ? | Ahmed (×2 : doublon signalé) et Salma |
| Liste les clients assurés par MedAssur. | Youssef Gharbi |
| Qui est assuré auprès de AssurTunis ? | idem *assures_compagnie* |
| quels sont les biens assures de ahmd | faute et accents tolérés (correspondance approchée) |
| Quels sont les biens de Mariem ? | « Mariem est un bénéficiaire, pas un assuré » |
| Quels sont les assurés de Zurich ? | compagnie inconnue + liste des compagnies connues |
| `biens de Ahmed" } DROP ALL #` | refusée : caractères SPARQL, aucune requête générée |

Pour chaque réponse, commenter les 3 panneaux : **1. analyse** (intention + score, signaux, mention, entité résolue, jetons
spaCy), **2. requête SPARQL générée** (template + `VALUES` avec identifiants validés), **3. résultats**.

**D. « STAR » (exemple de la consigne)** — la compagnie n'existe pas dans l'ontologie fournie : demander
« Quels sont les assurés de STAR ? » montre le message d'erreur et les suggestions. Puis : `/acteurs/nouveau/` → type
« Compagnie d'assurance », nom `STAR` ; `/contrats/nouveau/` → un contrat dont la compagnie émettrice est STAR et le souscripteur
Salma ; reposer la question → Salma Trabelsi, **sans HermiT** (le template passe par les contrats, pas seulement par
`estAssureurDe`).

## 4. Questions probables du professeur

**Pourquoi pas un LLM ?** Interdit par le sujet. Ici : spaCy pour l'analyse linguistique, règles d'intention explicables
(score visible), templates SPARQL écrits à la main. Tout est reproductible et testable.

**Où est spaCy utilisé ?** `nlp.analyser_texte` : tokenisation, lemmatisation, catégories, mots vides (retrait du « cadre » de la
question) et entités nommées (confirmation de la mention). Modèle `fr_core_news_sm`.

**Comment l'intention est-elle détectée ?** Chaque intention a des mots déclencheurs pondérés, comparés aux lemmes et aux formes
sans accents ; le meilleur score ≥ 2 gagne. « assurés » après « biens » ne compte pas (c'est un adjectif).

**Comment extrayez-vous « Ahmed » ?** On enlève les mots interrogatifs, verbes de demande, mots d'intention et mots vides ;
le groupe restant après « de / par / à / chez » est la mention. On la relie ensuite à un individu de l'ontologie.

**Et si deux Ahmed existent ?** Homonymes distincts → page de choix (puces cliquables). Mêmes nom + CIN → même personne
(doublon) : leurs identifiants sont regroupés dans le `VALUES`.

**Peut-on faire une injection SPARQL ?** Non, par construction : le texte saisi n'est jamais inséré dans la requête ; seuls des
identifiants trouvés dans l'ontologie (regex `[A-Za-z0-9_]+`) le sont. En plus : caractères `{ } < > ; \ |` refusés, garde-fou
`SELECT` seul, endpoint `/query` en lecture seule. Testé (`SecuriteTests`, `SecuriteIntegrationTests`).

**Pourquoi la requête combine `estAssureurDe` et les contrats ?** `estAssureurDe` est **inférée** par HermiT (chaîne
`emet ∘ estSouscritPar`). Fuseki ne lance pas HermiT : un assuré créé dans l'application n'a pas ce lien. Le chemin par les
contrats est toujours présent ; la propriété inférée couvre les données issues de l'export.

**Qu'est-ce que HermiT apporte ici ?** Il a validé la cohérence de l'ontologie et matérialisé les inférences (ex. `estAssureurDe`,
types `AssureAutomobiliste`). Je n'ai **pas modifié l'ontologie** : pas de nouvelle validation nécessaire. Les données ajoutées
par CRUD portent explicitement leurs classes (`Acteur` + sous-type) pour être visibles dans les listes.

**Quels axiomes respectez-vous dans le CRUD ?** `HasKey` (CIN des assurés, immatriculation des véhicules), `owl:oneOf` sur
`typeLogement`, facettes de datatype (bonus-malus, puissance fiscale, année, pièces, superficie, montants), propriétés inverses
(`appartientA` ↔ `estProprietaireDe`) et symétrique (`estCoAssureAvec`).

**Comment fonctionne le CRUD ?** SPARQL Update : `INSERT DATA` (création), `DELETE DATA` + `INSERT DATA` (modification),
`DELETE WHERE` (suppression et références). Les entrées passent par des littéraux échappés/validés (`rdf.chaine`, `rdf.decimal`…).

**Pourquoi `/assures/` ne propose-t-elle pas son propre CRUD ?** Pour ne pas dupliquer le moteur : elle ajoute une vue
spécialisée (biens, contrats, compagnies, doublons) et renvoie vers le CRUD `acteurs` avec `?next=` pour revenir à la liste.

**Limites ?** Petit modèle spaCy (lemmes et NER imparfaits, d'où les comparaisons sans accents et sur les formes) ; une seule
entité par question ; deux intentions pour ce membre ; pas de recalcul HermiT après CRUD (voulu, expliqué dans le guide).

**Comment avez-vous testé ?** 109 tests Django (unitaires NLP avec spaCy réel, intégration Fuseki, CRUD, formulaires, routes,
non-régression) sur un dataset de test isolé en mémoire ; le dataset principal n'est jamais écrit et sa taille est vérifiée.
