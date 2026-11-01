# Membre 3 — Acteurs, Biens assurés et NLP

Périmètre : classes `Acteur` et `BienAssure`, pages `/assures/`, `/acteurs/`, `/biens/`, module NLP
(intentions « biens d'un assuré » et « assurés d'une compagnie »), page `/question/`.

Voir aussi [soutenance.md](soutenance.md) (scénarios de démonstration et questions probables du professeur).

---

## 1. Architecture technique

```
Navigateur ──HTTP──> Django (views_*.py) ──> services/*.py ──SPARQLWrapper──> Fuseki (dataset « assurance »)
                         │                                                        ▲
                         └── nlp.py (spaCy) ── question → intention → entité → SPARQL ┘
```

| Fichier | Rôle |
|---|---|
| `app/sparql_service.py` | `query()` / `update()` vers Fuseki (SPARQLWrapper). URL surchargeable par `FUSEKI_URL`. |
| `app/services/rdf.py` | Littéraux SPARQL sûrs (`chaine`, `decimal`…), CRUD générique d'un individu (déjà existant, réutilisé). |
| `app/services/crud.py` | Moteur CRUD déclaratif (déjà existant, étendu de façon rétro-compatible, voir §4). |
| `app/services/acteurs.py` | Description de la classe `Acteur` pour le moteur CRUD (champs, relations, contrôles). |
| `app/services/biens.py` | Service `BienAssure` (liste, validation, CRUD écrits à la main car formulaire spécifique). |
| `app/services/assures.py` + `app/views_assures.py` | Page `/assures/` (lecture, recherche, filtres). |
| `app/nlp.py` | **Noyau NLP commun** : analyse spaCy, intentions, entités, exécution. |
| `app/intentions_membre3.py` | Les deux intentions du membre 3 (mots déclencheurs + templates SPARQL). |
| `app/views_nlp.py`, `templates/app/question.html` | Page « Poser une question ». |
| `app/tests_membre3/` | 109 tests (voir §9). |

Routes : `/assures/` (liste des assurés), `/acteurs/` (+ `nouveau/`, `<id>/modifier/`, `<id>/supprimer/`, routes
générées par le registre), `/biens/` (+ `nouveau/`, `<id>/modifier/`, `<id>/supprimer/`), `/question/`.
Le guide demande `/assures/` et `/biens/` : `/biens/` existait déjà (conservée), `/assures/` a été créée ;
le CRUD des assurés **réutilise** les routes `/acteurs/…` (pas de duplication) grâce au paramètre `?next=`
qui ramène l'utilisateur sur `/assures/` après l'action.

## 2. Ontologie : classes, propriétés et axiomes utilisés

Toutes les propriétés ont été **lues dans `assurance_inferee.owl`** (aucun nom inventé). Namespace :
`http://www.esprit.tn/ontologies/assurance-sinistres#`.

**Classes** : `Acteur` ⊇ `Assure` (⊇ `AssureAutomobiliste`, classe définie), `Expert`, `Beneficiaire`,
`CompagnieAssurance` ; `BienAssure` ⊇ `Vehicule`, `Logement`, `PersonneAssuree`.

**Propriétés d'objet (Acteur / BienAssure)**

| Propriété | Domaine → portée | Remarque |
|---|---|---|
| `appartientA` / `estProprietaireDe` | BienAssure → Assure / Assure → BienAssure | inverses |
| `souscrit` / `estSouscritPar` | Assure → Contrat / Contrat → Assure | inverses |
| `emet` / `estEmisPar` | Compagnie → Contrat / Contrat → Compagnie | inverses, `estEmisPar` fonctionnelle |
| `couvreBien` | ContratAssurance → BienAssure | pas d'inverse déclaré |
| `estAssureurDe` | Compagnie → Assure | **inférée par HermiT** : chaîne `emet ∘ estSouscritPar` |
| `estCoAssureAvec` | Assure → Assure | symétrique |
| `estReassurePar`, `collaboreAvec` | Compagnie → Compagnie, Expert → Compagnie | |

**Propriétés de données** : `nom`, `email`, `telephone` (Acteur) ; `cin`, `profession`, `anneesPermis`,
`coefficientBonusMalus`, `dateNaissance` (Assure) ; `specialite`, `numeroAgrement` (Expert) ;
`lienAvecAssure` (Beneficiaire) ; `matriculeFiscal`, `capitalSocial` (Compagnie) ;
`immatriculation`, `marque`, `modele`, `anneeMiseEnCirculation`, `puissanceFiscale`, `valeurVenale` (Vehicule) ;
`adresse`, `typeLogement`, `superficie`, `nombrePieces`, `valeurDeclaree` (Logement) ;
`numeroAffiliationCNAM`, `dateNaissance` (PersonneAssuree) ; `identifiant`, `montant`, `dateEvenement` (convention
de l'ontologie, remplies automatiquement).

**Axiomes qui contraignent l'application** (relevés dans le fichier OWL) :

| Axiome | Conséquence dans le code |
|---|---|
| `HasKey(Assure, cin)` | le CIN d'un assuré est unique (contrôle dans `acteurs.verifier_acteur`) |
| `HasKey(Vehicule, immatriculation)` | immatriculation unique, comparée sans espaces (`biens._cle_deja_prise`) |
| `typeLogement` ∈ `{Appartement, Duplex, Studio, Villa}` (`owl:oneOf`) | liste déroulante alignée sur l'ontologie |
| `coefficientBonusMalus` ∈ [0,5 ; 3,5] | validation du formulaire |
| `puissanceFiscale` ∈ [1 ; 50], `anneeMiseEnCirculation` ≥ 1950, `nombrePieces` ≥ 1, `anneesPermis` ≥ 0, `superficie` > 0, `montant` ≥ 0 | validation du formulaire |

## 3. Services Django et requêtes SPARQL

**Lecture `/biens/`** (`biens.lister`) : un `SELECT` avec un `OPTIONAL` par propriété, `GROUP_CONCAT` des propriétaires
(`appartientA`) et des contrats (`?ct :couvreBien ?b`), filtres `FILTER(CONTAINS(LCASE(...)))` (recherche) et
`FILTER(COALESCE(?valeurVenale, ?valeurDeclaree) >= …)`.

**Lecture `/assures/`** (`assures.lister`) : `?a a :Assure` + `OPTIONAL` des données, `COUNT(DISTINCT ?b)` des biens
(`estProprietaireDe` ∪ `appartientA`), `COUNT(DISTINCT ?c)` des contrats (`souscrit` ∪ `estSouscritPar`), compagnies via
`estAssureurDe` ∪ (`estSouscritPar` + `estEmisPar`). Filtre compagnie : `FILTER EXISTS { … }`.

**Écriture** (`rdf.py` / `crud.py`) : `INSERT DATA`, `DELETE DATA` (valeurs relues puis supprimées, car Jena ne retrouve pas
toujours un décimal avec `DELETE WHERE`), `DELETE WHERE { ?s ?p :individu }` pour retirer les références à la suppression.

## 4. Fonctionnement du CRUD

* **Acteur** : entité déclarative `ACTEUR` du moteur générique (`crud.py`). Un type (`Assure`, `Expert`, `Beneficiaire`,
  `CompagnieAssurance`) détermine les champs affichés. À la création sont écrites **explicitement** les classes
  (`Acteur` + sous-type), car Fuseki n'exécute pas HermiT. L'identifiant est préfixé par le sous-type
  (`Assure_Karim_Zouari`).
* **Relations RDF** : `estProprietaireDe` (↔ `appartientA`), `estCoAssureAvec` (symétrique), `collaboreAvec`,
  `estReassurePar` ; le moteur écrit la propriété **et son inverse**, et les retire de même à la modification.
* **BienAssure** : formulaire dédié (`bien_form.html`) avec multi-propriétaires et contrats couvrants
  (`couvreBien`, porté par le contrat). Le type ne change pas en édition.
* **Validation** : champs obligatoires, types (entier / décimal / date), facettes OWL (§2), formats (email, téléphone
  `+216 …`, CIN à 8 chiffres), clés OWL, existence des cibles de relation.
* **Messages** : succès (`messages.success`), erreurs de validation listées dans le formulaire, Fuseki arrêté →
  « Fuseki est injoignable », identifiant invalide → 404, suppression uniquement en `POST` avec boîte de confirmation.
* **Modifications du moteur commun** (rétro-compatibles, valeurs par défaut inchangées pour les autres membres) :
  `Champ.minimum/maximum`, `Entite.verifier` (contrôles métier), `Entite.prefixe_par_type`, paramètre `ident` de
  `crud.valider`, redirection sûre `?next=` (refuse les URL externes), type présélectionné par `?type=`.
* **Corrections apportées à l'existant** : « Maison » retirée de `typeLogement` (hors énumération OWL, rendrait l'ontologie
  incohérente sous HermiT) et « Duplex » ajoutée ; le propriétaire unique du formulaire des biens supprimait silencieusement
  le second propriétaire ; l'inverse `estProprietaireDe` n'était pas écrit ; un véhicule pouvait être recréé avec la même
  immatriculation écrite autrement (« 123TU4567 » / « 123 TU 4567 »).

## 5. Fonctionnement du NLP (spaCy)

Aucun LLM, aucune API externe : analyse linguistique **spaCy `fr_core_news_sm` 3.8.0**, règles d'intention et templates SPARQL.

1. **Nettoyage** (`nlp.nettoyer`) : normalisation Unicode, apostrophes typographiques, suppression des guillemets ;
   refus d'une question vide, de plus de 300 caractères, ou contenant `{ } < > ; \ |` (caractères SPARQL).
2. **Analyse spaCy** : tokens, lemmes, catégories grammaticales, mots vides, entités nommées.
3. **Intention** : chaque intention donne un score à partir de mots déclencheurs comparés aux **formes et aux lemmes sans
   accents** (le lemmatiseur du petit modèle est imparfait : « assurés » → « assuré »/« assurer »). Exemple : « biens » = +3,
   « appartenant » = +1 pour *biens_assure* ; « assurés »/« clients » = +2, « compagnie », « auprès de »/« chez » = +1 pour
   *assures_compagnie*. Règle de désambiguïsation : « assurés » juste après « biens » qualifie les biens et ne compte pas.
   Seuil 2 ; égalité ou score insuffisant → « intention non reconnue ».
4. **Mention d'entité** : on retire le cadre de la question (mots interrogatifs, verbes de demande, mots d'intention,
   mots vides spaCy) ; le groupe restant situé après « de / par / à / chez… » est le nom cherché
   (« Ahmed », « Ahmed Ben Salah », « AssurTunis »). Les entités nommées spaCy servent de confirmation affichée.
5. **Résolution dans l'ontologie** : le référentiel des acteurs est lu dans Fuseki. Niveaux : 3 = nom complet ou
   identifiant complet, 2 = tous les mots du nom présents (« Ahmed » ⊂ « Ahmed Ben Salah »), 1 = approchée
   (similarité ≥ 0,82, fautes de frappe). Les doublons d'une même personne (même nom + même CIN, ex.
   `Assure_Ahmed` / `Client_CRM_4471`) sont regroupés ; des homonymes distincts donnent une **demande de précision**
   (puces cliquables) ; un nom d'un autre type (« Mariem » est une bénéficiaire) ou inconnu donne un message clair avec
   des suggestions.
6. **Requête SPARQL par template** : le texte saisi n'est **jamais** concaténé. Seuls des identifiants d'individus issus de
   l'ontologie (regex `[A-Za-z0-9_]+`) sont insérés dans `VALUES ?assure { … }`. Un garde-fou (`verifier_requete`) n'accepte
   que `SELECT` ; l'exécution passe par l'endpoint `/query` (lecture seule).
7. **Affichage** : question nettoyée, intention et score, signaux, mention extraite, entité résolue, entités spaCy, scores de
   toutes les intentions, jetons, requête générée, résultats.

Requête de l'intention *assures_compagnie* (extrait) — le chemin explicite par les contrats est combiné à la propriété
inférée, pour fonctionner aussi avec des données créées par l'application (non classées par HermiT) :

```sparql
SELECT ?assure (SAMPLE(?n) AS ?nom) ... WHERE {
  VALUES ?compagnie { :AssurTunis }
  { ?compagnie :estAssureurDe ?assure }
  UNION { ?compagnie :emet ?contrat . ?contrat :estSouscritPar ?assure }
  UNION { ?contrat :estEmisPar ?compagnie ; :estSouscritPar ?assure }
  OPTIONAL { ?assure :nom ?n } ...
} GROUP BY ?assure
```

« Biens assurés d'un assuré » = biens dont il est propriétaire (`estProprietaireDe` ∪ `appartientA`) **ou** couverts par un
contrat qu'il a souscrit (`estSouscritPar` + `couvreBien`).

**Étendre le NLP (autres membres)** : créer `app/intentions_membre<N>.py` avec `nlp.enregistrer(nlp.Intention(...))`
(score, mots du cadre, référentiel, classes attendues, template, colonnes) puis ajouter une ligne
`from . import intentions_membre<N>` à la fin de `nlp.py`.

## 6. Écarts constatés entre les sources

* Le guide cite Fuseki 6.2.0 / Java 21 ; la machine a **Java 17** → Fuseki **5.6.0** (conforme à la remarque du guide et à
  Asma). Le guide évoque `assurance_sinistres.owl` (ontologie source) et `assurance_inferee.owl` (export HermiT) : seul
  `assurance_inferee.owl` est chargé.
* La mission cite l'exemple « STAR » : **aucune compagnie STAR n'existe dans `assurance_inferee.owl`** (compagnies :
  AssurTunis, MedAssur, TunisRe, GlobalRe). Les démonstrations utilisent AssurTunis / MedAssur ; « STAR » renvoie un message
  explicite et se démontre après création de la compagnie dans l'application (voir soutenance). Les tests utilisent
  un jeu d'essai contenant STAR, uniquement dans le dataset de test.
* `Client_CRM_4471` est un doublon d'`Assure_Ahmed` (même CIN, même nom). Le CIN étant une clé (`HasKey`), HermiT devrait les
  identifier ; l'export ne contient pas de `owl:sameAs`. L'application les signale comme doublons sans les fusionner.
* `fr_core_news_sm` étiquette parfois les noms propres en NOUN et « Quels » en LOC : l'extraction ne dépend donc pas de la NER.

## 7. Installation et exécution (Windows / PowerShell)

Versions réellement utilisées : Java 17.0.12 · Apache Jena Fuseki 5.6.0 · Python 3.14.4 · Django 5.2.18 ·
SPARQLWrapper 2.0.0 · rdflib 7.6.0 · spaCy 3.8.18 + `fr_core_news_sm` 3.8.0.

```powershell
# 1. Fuseki (terminal 1) — archive officielle https://archive.apache.org/dist/jena/binaries/
cd <dossier>\apache-jena-fuseki-5.6.0
.\fuseki-server.bat                       # http://localhost:3030

# 2. Dataset « assurance » (TDB2) et chargement de l'ontologie (une seule fois)
curl.exe -X POST -d "dbName=assurance&dbType=tdb2" http://localhost:3030/$/datasets
curl.exe -X POST -H "Content-Type: application/rdf+xml" --data-binary "@docs/references/assurance_inferee.owl" http://localhost:3030/assurance/data

# 3. Django (terminal 2)
cd D:\semantique
python -m venv .venv ; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m spacy download fr_core_news_sm
python manage.py migrate
python manage.py runserver                # http://127.0.0.1:8000
```

Vérification : requête du guide (`numeroDossier` / `statutDossier`) → **5 sinistres** ; `/`, `/sinistres/`, `/contrats/`,
`/garanties/`, `/biens/`, `/acteurs/`, `/assures/`, `/question/` répondent 200.

## 8. Protection des données

Les tests n'écrivent **jamais** dans `assurance` : ils utilisent le dataset **en mémoire** `assurance_member3_test`
(créé automatiquement, réinitialisé avant chaque test avec l'ontologie officielle puis un jeu d'essai). Un garde-fou
vérifie avant et après la suite que le nombre de triplets de `assurance` n'a pas changé (2 651).
La variable `FUSEKI_URL` permet de pointer l'application vers un autre dataset.

> Remarque : un premier dataset de test TDB2, vidé et rechargé avant chaque test, a fini par bloquer Jena 5.6.0
> (boucle dans `DROP ALL`). Le dataset de test est donc volontairement en mémoire.

## 9. Tests

```powershell
python manage.py test app            # nécessite Fuseki lancé
```

| Fichier | Tests | Contenu |
|---|---|---|
| `test_nlp_unitaire.py` | 24 | nettoyage, intentions, mentions, résolution (doublons, ambiguïté, fautes, mauvais type), sécurité (spaCy réel, sans Fuseki) |
| `test_nlp_integration.py` | 23 | questions → SPARQL → Fuseki, injections, page `/question/`, scénarios de démonstration |
| `test_crud_acteurs.py` | 27 | CRUD acteurs/assurés, facettes OWL, clé CIN, relations et inverses, redirections `?next=`, page `/assures/` |
| `test_crud_biens.py` | 22 | CRUD biens, énumération et facettes OWL, clé immatriculation, relations, liste/filtres/recherche |
| `test_routes_regression.py` | 13 | routes, menu, non-régression des autres modules (sinistres = 5, contrats, expertises, accueil) |

Résultat de l'exécution finale : voir le rapport de fin de mission (109 tests).
