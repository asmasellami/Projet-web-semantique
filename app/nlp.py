"""Module NLP / TALN commun : question en français -> intention -> entités -> requête SPARQL -> résultats.

Approche explicable (aucun LLM, aucune API externe) :

1. Analyse linguistique avec spaCy (modèle fr_core_news_sm) : tokens, lemmes, catégories, entités nommées.
2. Détection de l'intention par règles pondérées : chaque intention déclare des mots déclencheurs
   (comparés aux lemmes ET aux formes, sans accents) ; l'intention au meilleur score l'emporte.
3. Extraction de la mention d'entité : on retire le « cadre » de la question (mots interrogatifs,
   verbes de demande, mots d'intention, mots vides spaCy) ; ce qui reste est le nom cherché.
4. Résolution de l'entité dans l'ontologie (référentiel lu dans Fuseki) : correspondance exacte,
   par inclusion de mots, puis approchée (fautes de frappe). Les doublons d'un même individu
   (même nom et même CIN) sont regroupés ; les homonymes distincts déclenchent une demande de précision.
5. Génération de la requête SPARQL par TEMPLATE : le texte de l'utilisateur n'est JAMAIS inséré dans la
   requête. Seuls des identifiants d'individus déjà présents dans l'ontologie (validés par expression
   régulière) y figurent. L'injection SPARQL est donc impossible par construction.
6. Exécution en lecture seule (endpoint /query) via sparql_service, puis mise en forme des résultats.

Chaque membre ajoute ses intentions dans son propre fichier (voir intentions_membre3.py) en appelant
`enregistrer(Intention(...))`, sans modifier ce noyau commun.
"""
import difflib
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Callable

from . import sparql_service
from .services import rdf

MODELE_SPACY = "fr_core_news_sm"
LONGUEUR_MAX = 300
SEUIL_INTENTION = 2.0          # score minimal pour retenir une intention
SEUIL_APPROX = 0.82            # similarité minimale d'une correspondance approchée
CARACTERES_INTERDITS = set("{}<>;\\|`")
GUILLEMETS = '"«»“”„'

# Mots du « cadre » d'une question : jamais pris pour un nom d'entité.
CADRE_COMMUN = {
    "quel", "quels", "quelle", "quelles", "qui", "que", "quoi", "est", "sont", "etre", "liste", "lister",
    "montre", "montrer", "affiche", "afficher", "donne", "donner", "voir", "trouve", "trouver", "cherche",
    "chercher", "veux", "voudrais", "souhaite", "savoir", "connaitre", "tous", "toutes", "tout", "svp",
    "stp", "merci", "bonjour", "peux", "pouvez", "peut", "moi", "nous", "me", "il", "y", "a", "ont",
    "avoir", "existe", "existent", "combien", "nombre", "voici",
}
# Mots qui introduisent généralement le complément (« de Ahmed », « auprès de STAR »).
MARQUEURS = {"de", "d", "du", "des", "par", "a", "au", "aux", "chez", "aupres", "pour"}


LIBELLES_TYPES = {"Assure": "assuré", "CompagnieAssurance": "compagnie d'assurance", "Expert": "expert",
                  "Beneficiaire": "bénéficiaire"}


class QuestionInvalide(ValueError):
    """Question refusée avant toute analyse (vide, trop longue, caractères SPARQL)."""


class ModeleIndisponible(RuntimeError):
    """Le modèle spaCy français n'est pas installé."""


# ---------- Utilitaires de texte ----------
def sans_accents(texte):
    """Minuscules sans accents : « Léïla » -> « leila »."""
    decompose = unicodedata.normalize("NFKD", texte)
    return "".join(c for c in decompose if not unicodedata.combining(c)).casefold()


def nettoyer(question):
    """Normalise la question ou lève QuestionInvalide. Aucun caractère propre à SPARQL n'est toléré."""
    if not isinstance(question, str) or not question.strip():
        raise QuestionInvalide("Veuillez saisir une question.")
    texte = unicodedata.normalize("NFC", question)
    texte = texte.replace("’", "'").replace("‘", "'").replace("`", "'")
    if any(c in CARACTERES_INTERDITS for c in texte):
        raise QuestionInvalide("Question refusée : elle contient des caractères réservés au langage SPARQL "
                               "( { } < > ; \\ | ). Posez une question en français simple.")
    texte = "".join(c if c.isprintable() or c.isspace() else " " for c in texte)
    for g in GUILLEMETS:
        texte = texte.replace(g, " ")
    texte = re.sub(r"\s+", " ", texte).strip()
    if not texte:
        raise QuestionInvalide("Veuillez saisir une question.")
    if len(texte) > LONGUEUR_MAX:
        raise QuestionInvalide(f"Question trop longue ({len(texte)} caractères, maximum {LONGUEUR_MAX}).")
    return texte


_modele = None


def modele():
    """Charge spaCy une seule fois."""
    global _modele
    if _modele is None:
        try:
            import spacy
            _modele = spacy.load(MODELE_SPACY)
        except (ImportError, OSError) as err:
            raise ModeleIndisponible(
                f"Modèle spaCy « {MODELE_SPACY} » introuvable : python -m spacy download {MODELE_SPACY}") from err
    return _modele


# ---------- Analyse linguistique ----------
@dataclass
class Jeton:
    texte: str
    lemme: str
    pos: str
    mot_vide: bool
    ponctuation: bool
    forme: str = ""            # texte sans accents, minuscules
    lemme_na: str = ""         # lemme sans accents, minuscules


@dataclass
class Contexte:
    question: str
    nettoyee: str
    jetons: list
    entites_nommees: list      # [(texte, étiquette spaCy)]


def analyser_texte(question):
    """Étape 1 : nettoyage + analyse spaCy."""
    nettoyee = nettoyer(question)
    doc = modele()(nettoyee)
    jetons = [Jeton(t.text, t.lemma_, t.pos_, t.is_stop, t.is_punct or t.is_space,
                    sans_accents(t.text), sans_accents(t.lemma_)) for t in doc]
    return Contexte(question, nettoyee, jetons, [(e.text, e.label_) for e in doc.ents])


# ---------- Intentions ----------
@dataclass
class EntiteConnue:
    """Individu de l'ontologie pouvant être cité dans une question."""
    id: str
    nom: str = ""
    types: set = field(default_factory=set)
    cin: str = ""

    @property
    def etiquettes(self):
        court = self.id.split("_", 1)[-1].replace("_", " ")
        return [x for x in (self.nom, court, self.id.replace("_", " ")) if x]

    @property
    def libelle(self):
        return self.nom or self.id.replace("_", " ")


@dataclass
class Intention:
    nom: str                                   # identifiant technique
    libelle: str                               # affiché dans l'interface
    exemples: list                             # questions d'exemple (cliquables)
    score: Callable                            # (Contexte) -> (score, [signaux])
    mots_cadre: set                            # mots d'intention retirés avant l'extraction de l'entité
    referentiel: Callable                      # () -> [EntiteConnue]
    types_attendus: tuple                      # classes OWL acceptées pour l'entité (ex. ("Assure",))
    nom_type: str                              # « assuré », « compagnie » (messages)
    construire: Callable                       # ([id d'individus validés]) -> texte SPARQL (SELECT)
    colonnes: list                             # [(variable SPARQL, libellé de colonne)]
    formater: Callable | None = None           # (lignes) -> lignes enrichies (facultatif)


INTENTIONS: dict = {}


def enregistrer(intention):
    """Ajoute une intention au moteur (appelé par le fichier de chaque membre)."""
    INTENTIONS[intention.nom] = intention
    return intention


def cherche(ctx, mots, poids, sauf_apres=frozenset()):
    """Cumule `poids` pour chaque jeton dont la forme ou le lemme (sans accents) est dans `mots`.

    `sauf_apres` : le jeton est ignoré s'il suit directement l'un de ces mots
    (« biens assurés » : « assurés » qualifie les biens, il n'annonce pas la question sur les assurés).
    """
    score, trouves = 0.0, []
    for i, j in enumerate(ctx.jetons):
        if j.forme in mots or j.lemme_na in mots:
            precedent = ctx.jetons[i - 1] if i else None
            if precedent and (precedent.forme in sauf_apres or precedent.lemme_na in sauf_apres):
                continue
            score += poids
            trouves.append(f"« {j.texte} » (+{poids:g})")
    return score, trouves


def detecter_intention(ctx):
    """Étape 2 : retourne (intention retenue | None, tableau des scores)."""
    resultats = []
    for intention in INTENTIONS.values():
        s, signaux = intention.score(ctx)
        resultats.append({"intention": intention, "score": s, "signaux": signaux})
    resultats.sort(key=lambda r: -r["score"])
    meilleur = resultats[0] if resultats else None
    if not meilleur or meilleur["score"] < SEUIL_INTENTION:
        return None, resultats
    if len(resultats) > 1 and resultats[1]["score"] == meilleur["score"]:
        return None, resultats         # égalité : intention ambiguë
    return meilleur, resultats


# ---------- Extraction de la mention ----------
def extraire_mention(ctx, intention):
    """Étape 3 : retourne (mention | "", avertissements). Les mots du cadre sont retirés."""
    cadre = set(CADRE_COMMUN)
    for i in INTENTIONS.values():
        cadre |= i.mots_cadre

    def dans_cadre(j):
        return j.ponctuation or j.mot_vide or j.forme in cadre or j.lemme_na in cadre

    runs, courant = [], []
    for i, j in enumerate(ctx.jetons):
        if j.texte == "-" and courant and i + 1 < len(ctx.jetons) and not dans_cadre(ctx.jetons[i + 1]):
            continue                    # trait d'union à l'intérieur d'un nom (Ben-Salah)
        if dans_cadre(j):
            if courant:
                runs.append(courant)
            courant = []
        else:
            courant.append(i)
    if courant:
        runs.append(courant)

    if not runs:
        return "", []

    def apres_marqueur(run):
        precedent = ctx.jetons[run[0] - 1] if run[0] else None
        return bool(precedent and precedent.forme.rstrip("'") in MARQUEURS)

    choisis = [r for r in runs if apres_marqueur(r)]
    run = choisis[-1] if choisis else max(runs, key=len)
    mention = " ".join(ctx.jetons[i].texte for i in run)
    avert = []
    if len(runs) > 1:
        autres = [" ".join(ctx.jetons[i].texte for i in r) for r in runs if r is not run]
        avert.append(f"Plusieurs groupes de mots détectés ; seul « {mention} » est utilisé "
                     f"(ignoré : {', '.join(autres)}).")
    return mention, avert


# ---------- Référentiel et résolution d'entité ----------
def charger_entites(classe, sous_classes=(), prop_nom="nom", prop_cle="cin"):
    """Lit dans Fuseki les individus d'une classe (id, nom, clé, types) pour la résolution."""
    valeurs = " ".join(f":{c}" for c in sous_classes)
    typage = f"OPTIONAL {{ ?s a ?t . VALUES ?t {{ {valeurs} }} }}" if valeurs else ""
    rows = sparql_service.query(f"""
        SELECT ?s ?nom ?cle ?t WHERE {{
            ?s a :{classe} .
            OPTIONAL {{ ?s :{prop_nom} ?nom }}
            OPTIONAL {{ ?s :{prop_cle} ?cle }}
            {typage}
        }}""")
    connues = {}
    for r in rows:
        ident = rdf.local(r["s"]["value"])
        e = connues.setdefault(ident, EntiteConnue(ident))
        e.nom = e.nom or r.get("nom", {}).get("value", "")
        e.cin = e.cin or r.get("cle", {}).get("value", "")
        if "t" in r:
            e.types.add(rdf.local(r["t"]["value"]))
    return sorted(connues.values(), key=lambda e: e.id)


def _correspondance(mention_na, entite):
    """Niveau de correspondance : 3 exacte, 2 par inclusion de mots, 1 approchée, 0 aucune."""
    etiquettes = [sans_accents(x) for x in entite.etiquettes]
    mots_mention = mention_na.split()
    exactes = [sans_accents(x) for x in (entite.nom, entite.id.replace("_", " ")) if x]
    if mention_na in exactes:          # nom complet ou identifiant complet (l'id court ne suffit pas)
        return 3
    mots_entite = {m for x in etiquettes for m in re.split(r"[\s_]+", x) if m}
    if mots_mention and all(m in mots_entite for m in mots_mention):
        return 2
    if any(difflib.SequenceMatcher(None, mention_na, x).ratio() >= SEUIL_APPROX for x in etiquettes):
        return 1
    if mots_mention and all(any(difflib.SequenceMatcher(None, m, e).ratio() >= SEUIL_APPROX for e in mots_entite)
                            for m in mots_mention):
        return 1
    return 0


def _grouper(entites):
    """Regroupe les doublons d'un même individu (même nom et même CIN) en une seule personne."""
    groupes = {}
    for e in entites:
        cle = (sans_accents(e.nom), e.cin) if e.nom and e.cin else (e.id,)
        groupes.setdefault(cle, []).append(e)
    return list(groupes.values())


@dataclass
class Resolution:
    statut: str                    # trouvee | inconnue | ambigue | autre_type
    groupes: list = field(default_factory=list)       # [[EntiteConnue]] (un groupe = une personne / société)
    niveau: int = 0
    message: str = ""
    suggestions: list = field(default_factory=list)


def resoudre(mention, intention, referentiel):
    """Étape 4 : retrouve l'entité citée parmi les individus du type attendu."""
    mention_na = sans_accents(mention)
    attendus = set(intention.types_attendus)
    du_bon_type = [e for e in referentiel if e.types & attendus]

    def meilleurs(liste):
        scores = [(_correspondance(mention_na, e), e) for e in liste]
        niveau = max((s for s, _ in scores), default=0)
        return niveau, [e for s, e in scores if s == niveau and niveau > 0]

    niveau, trouves = meilleurs(du_bon_type)
    if trouves:
        # Les doublons d'une même personne (même nom + même CIN) sont toujours regroupés, même si
        # l'un d'eux n'est trouvé que par son nom complet et l'autre par son identifiant.
        groupes = _grouper(du_bon_type)
        groupes = [g for g in groupes if any(e in trouves for e in g)]
        statut = "trouvee" if len(groupes) == 1 else "ambigue"
        return Resolution(statut, groupes, niveau)

    autres = [e for e in referentiel if not e.types & attendus]
    _, ailleurs = meilleurs(autres)
    if ailleurs:
        e = ailleurs[0]
        genre = " / ".join(LIBELLES_TYPES.get(t, t) for t in sorted(e.types)) or "un autre type d'acteur"
        return Resolution("autre_type", _grouper(ailleurs), 0,
                          f"« {e.libelle} » est enregistré comme {genre}, pas comme {intention.nom_type}.")
    proches = sorted(du_bon_type, key=lambda e: -max(
        difflib.SequenceMatcher(None, mention_na, sans_accents(x)).ratio() for x in e.etiquettes))
    return Resolution("inconnue", [], 0,
                      f"Aucun(e) {intention.nom_type} nommé(e) « {mention} » dans l'ontologie.",
                      [e.libelle for e in proches[:5]])


# ---------- Réponse complète ----------
@dataclass
class Reponse:
    question: str
    statut: str = "invalide"       # ok | vide | invalide | intention_inconnue | entite_manquante | entite_inconnue
    #                                autre_type | ambigue | erreur_fuseki | erreur
    message: str = ""
    nettoyee: str = ""
    jetons: list = field(default_factory=list)
    entites_nommees: list = field(default_factory=list)
    scores: list = field(default_factory=list)
    intention: Intention | None = None
    score: float = 0.0
    signaux: list = field(default_factory=list)
    mention: str = ""
    confirmee_ner: bool = False    # la mention recoupe une entité nommée repérée par spaCy
    avertissements: list = field(default_factory=list)
    niveau_resolution: int = 0
    resolution: Resolution | None = None
    entites: list = field(default_factory=list)       # EntiteConnue retenues (individus d'une même personne)
    requete: str = ""
    colonnes: list = field(default_factory=list)
    lignes: list = field(default_factory=list)
    duree_ms: int = 0


NIVEAUX = {3: "exacte", 2: "par inclusion de mots", 1: "approchée (fautes de frappe)", 0: "—"}

_IDENT = re.compile(r"[A-Za-z0-9_]+")
_ECRITURE = re.compile(r"\b(INSERT|DELETE|DROP|CLEAR|LOAD|CREATE|COPY|MOVE|ADD|SERVICE|WITH)\b", re.I)


def verifier_requete(texte):
    """Garde-fou : seule une requête SELECT sans mot-clé d'écriture est exécutée."""
    corps = re.sub(r'"[^"\n]*"', '""', texte)
    if not re.search(r"^\s*SELECT\b", re.sub(r"(?im)^\s*(PREFIX[^\n]*|#[^\n]*)\n", "", corps)) or _ECRITURE.search(corps):
        raise ValueError("Requête non autorisée : seule la lecture (SELECT) est permise.")


def _valeur(binding):
    v = binding["value"]
    if binding["type"] == "uri":
        return rdf.libelle(v)
    if binding.get("datatype", "").endswith("#dateTime"):
        return v[:10]
    return v


def tableau(intention, bindings):
    lignes = [{var: _valeur(r[var]) if var in r else "" for var, _ in intention.colonnes} for r in bindings]
    return intention.formater(lignes) if intention.formater else lignes


def repondre(question, entite="", referentiel=None, executer=True):
    """Chaîne complète. `entite` : identifiants (séparés par des virgules) choisis après une ambiguïté.

    `referentiel` (liste d'EntiteConnue) et `executer=False` permettent de tester sans Fuseki.
    """
    debut = time.perf_counter()
    rep = Reponse(question=question or "")
    try:
        ctx = analyser_texte(question)
    except QuestionInvalide as err:
        rep.statut = "vide" if "saisir" in str(err) else "invalide"
        rep.message = str(err)
        return rep
    except ModeleIndisponible as err:
        rep.statut, rep.message = "erreur", str(err)
        return rep
    rep.nettoyee, rep.jetons, rep.entites_nommees = ctx.nettoyee, ctx.jetons, ctx.entites_nommees

    retenue, rep.scores = detecter_intention(ctx)
    if retenue is None:
        rep.statut = "intention_inconnue"
        rep.message = ("Intention non reconnue. Reformulez votre question, par exemple : "
                       + " · ".join(i.exemples[0] for i in INTENTIONS.values() if i.exemples))
        return rep
    intention = rep.intention = retenue["intention"]
    rep.score, rep.signaux = retenue["score"], retenue["signaux"]

    rep.mention, rep.avertissements = extraire_mention(ctx, intention)
    mention_na = sans_accents(rep.mention)
    rep.confirmee_ner = bool(mention_na) and any(
        mention_na in sans_accents(t) or sans_accents(t) in mention_na for t, _ in ctx.entites_nommees)
    if not rep.mention and not entite:
        rep.statut = "entite_manquante"
        rep.message = f"Précisez le nom de l'{intention.nom_type} concerné(e), par exemple : {intention.exemples[0]}"
        return rep

    try:
        if referentiel is None:
            referentiel = intention.referentiel()
        rep.resolution = res = resoudre(rep.mention, intention, referentiel)
        if entite:                                      # choix explicite parmi les candidats proposés
            ids = [x for x in entite.split(",") if _IDENT.fullmatch(x)]
            choisies = [e for e in referentiel if e.id in ids and e.types & set(intention.types_attendus)]
            if not choisies:
                rep.statut, rep.message = "entite_inconnue", "Individu choisi introuvable dans l'ontologie."
                return rep
            res = rep.resolution = Resolution("trouvee", [choisies], 3)
        rep.niveau_resolution = res.niveau
        if res.statut != "trouvee":
            rep.statut = {"inconnue": "entite_inconnue", "ambigue": "ambigue", "autre_type": "autre_type"}[res.statut]
            rep.message = res.message or (f"Plusieurs {intention.nom_type}s correspondent à « {rep.mention} » : "
                                          "choisissez celui que vous visez.")
            return rep
        rep.entites = res.groupes[0]
        ids = [e.id for e in rep.entites]
        if not all(_IDENT.fullmatch(i) for i in ids):   # identifiants issus de l'ontologie, jamais du texte libre
            raise ValueError("Identifiant d'individu invalide.")
        texte = intention.construire(ids)
        verifier_requete(texte)
        rep.requete = sparql_service.PREFIX + texte
        rep.colonnes = [lib for _, lib in intention.colonnes]
        if executer:
            rep.lignes = tableau(intention, sparql_service.query(texte))
        rep.statut = "ok"
        if executer and not rep.lignes:
            rep.message = f"Aucun résultat pour « {rep.entites[0].libelle} »."
    except OSError as err:                              # URLError / ConnectionError : Fuseki arrêté
        rep.statut, rep.message = "erreur_fuseki", f"Fuseki est injoignable ({err})."
    except Exception as err:                            # SPARQLWrapper lève des erreurs variées
        rep.statut, rep.message = "erreur", f"Erreur pendant l'exécution : {err}"
    rep.duree_ms = round((time.perf_counter() - debut) * 1000)
    return rep


# Les intentions de chaque membre s'enregistrent à l'import de leur fichier.
from . import intentions_membre3  # noqa: E402,F401
