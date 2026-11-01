"""Moteur CRUD déclaratif.

Un membre décrit sa classe (champs, types, relations) dans son fichier de service ;
ce module génère toutes les requêtes SPARQL (recherche, filtres, création,
modification, suppression). Aucune requête SPARQL à écrire à la main.
"""
import uuid
from dataclasses import dataclass, field

from app.sparql_service import query, update
from . import rdf


@dataclass
class Champ:
    cle: str                  # nom de la propriété dans l'ontologie (ex. "montantVerse")
    libelle: str              # libellé affiché
    genre: str = "texte"      # texte | zone | entier | decimal | date | booleen | choix | relation
    obligatoire: bool = False
    choix: tuple = ()         # valeurs possibles (genre "choix")
    cible: str = ""           # classe visée (genre "relation")
    inverse: str = ""         # propriété inverse à maintenir (genre "relation")
    pour: tuple = ()          # sous-types concernés ; vide = tous
    liste: bool = False       # colonne du tableau
    filtre: bool = False      # filtre déroulant (genre "choix")


@dataclass
class Entite:
    slug: str                 # URL et nom de route : /<slug>/
    classe: str               # classe de l'ontologie
    singulier: str
    pluriel: str
    module: str               # dossier de templates : templates/app/<module>/
    champs: list
    cle: str = ""             # champ qui fabrique l'identifiant (vide = identifiant aléatoire)
    sous_types: dict = field(default_factory=dict)   # {classe: libellé}
    derives: dict = field(default_factory=dict)      # {propriété: [champs sources]} (convention de l'ontologie)
    dates_evenement: bool = False                    # recopie les dates dans :dateEvenement
    champ_montant: str = ""   # champ numérique filtrable (min / max)
    feminin: bool = False
    liste_perso: bool = False  # la page liste existe déjà (route écrite à la main)

    @property
    def colonnes(self):
        """En-têtes du tableau. Les champs propres à un sous-type sont regroupés dans « Détails »."""
        cols = [c.libelle for c in self.champs if c.liste and not c.pour]
        if any(c.liste and c.pour for c in self.champs):
            cols.append("Détails")
        return cols

    @property
    def cree(self):
        return "créée" if self.feminin else "créé"

    @property
    def modifie(self):
        return "modifiée" if self.feminin else "modifié"

    @property
    def supprime(self):
        return "supprimée" if self.feminin else "supprimé"


CONVERSION = {"texte": rdf.chaine, "zone": rdf.chaine, "choix": rdf.chaine,
              "entier": rdf.entier, "decimal": rdf.decimal, "date": rdf.date_heure}


def champs_pour(e, type_):
    return [c for c in e.champs if not c.pour or type_ in c.pour]


# ---------- Recherche et filtrage ----------
def lister(e, params):
    """params : q, type, min, max et un filtre par champ « filtre ». Retourne (lignes, stats)."""
    colonnes = [c for c in e.champs if c.liste]
    communes = [c for c in colonnes if not c.pour]
    specifiques = [c for c in colonnes if c.pour]
    scalaires = {c.cle: c for c in e.champs
                 if c.genre != "relation" and (c.liste or c.filtre or c.cle == e.champ_montant)}

    optionnels, selects, filtres = [], [], ""
    for c in scalaires.values():
        optionnels.append(f"OPTIONAL {{ ?s :{c.cle} ?v_{c.cle} }}")
    for c in colonnes:
        if c.genre == "relation":
            optionnels.append(f'OPTIONAL {{ ?s :{c.cle} ?r_{c.cle} . '
                              f'BIND(STRAFTER(STR(?r_{c.cle}), "#") AS ?n_{c.cle}) }}')
            selects.append(f'(GROUP_CONCAT(DISTINCT ?n_{c.cle}; separator="|") AS ?a_{c.cle})')
        else:
            selects.append(f"(SAMPLE(?v_{c.cle}) AS ?a_{c.cle})")

    if e.sous_types:
        valeurs = " ".join(f":{t}" for t in e.sous_types)
        optionnels.append(f"OPTIONAL {{ ?s a ?t . VALUES ?t {{ {valeurs} }} }}")
        selects.append("(SAMPLE(?t) AS ?a_type)")
        if params.get("type") in e.sous_types:
            filtres += f"?s a :{params['type']} .\n"

    q = rdf.texte_filtre(params.get("q", ""))
    if q:
        textes = ", ".join(f'" ", COALESCE(STR(?v_{c.cle}), "")'
                          for c in scalaires.values() if c.genre in ("texte", "zone", "choix"))
        texte = f"CONCAT(STR(?s){', ' + textes if textes else ''})"
        filtres += f'FILTER(CONTAINS(LCASE({texte}), LCASE("{q}")))\n'

    for c in e.champs:
        valeur = params.get(c.cle, "")
        if c.filtre and valeur in c.choix:
            filtres += f"FILTER(?v_{c.cle} = {rdf.chaine(valeur)})\n"
    if e.champ_montant:
        for cle, op in (("min", ">="), ("max", "<=")):
            if params.get(cle):
                filtres += f"FILTER(?v_{e.champ_montant} {op} {rdf.decimal(params[cle])})\n"

    nl = "\n            "
    rows = query(f"""
        SELECT ?s {' '.join(selects)}
        WHERE {{
            ?s a :{e.classe} .
            {nl.join(optionnels)}
            {filtres}
        }}
        GROUP BY ?s
        ORDER BY ?s
    """)

    lignes = []
    for r in rows:
        def val(cle):
            return r.get(cle, {}).get("value", "")
        def formater(c):
            brut = val(f"a_{c.cle}")
            if c.genre == "relation":
                return [x.replace("_", " ") for x in brut.split("|") if x]
            if c.genre == "booleen":
                return {"true": "Oui", "false": "Non"}.get(brut, "—") if brut else ""
            if c.genre == "date":
                return brut[:10]
            return brut

        cellules = [{"genre": c.genre, "valeur": formater(c) or ("—" if c.genre == "booleen" else "")}
                    for c in communes]
        if specifiques:
            # Champs propres au sous-type de cette ligne : « Libellé : valeur »
            code_type = rdf.local(val("a_type"))
            details = []
            for c in specifiques:
                v = formater(c)
                if v and (not code_type or code_type in c.pour):
                    details.append(f"{c.libelle} : {', '.join(v) if isinstance(v, list) else v}")
            cellules.append({"genre": "details", "valeur": details})
        code_type = rdf.local(val("a_type"))
        lignes.append({
            "id": rdf.local(r["s"]["value"]),
            "type": e.sous_types.get(code_type, ""),
            "cellules": cellules,
        })

    stats = {"total": len(lignes), "par_type": []}
    for code, nom in e.sous_types.items():
        n = sum(1 for l in lignes if l["type"] == nom)
        if n:
            stats["par_type"].append((nom, n))
    return lignes, stats


# ---------- Lecture d'un individu ----------
def charger(e, ident):
    """(type, valeurs du formulaire) ou None si l'individu n'existe pas dans cette classe."""
    if not query(f"SELECT ?x WHERE {{ :{ident} a :{e.classe} }} LIMIT 1"):
        return None
    type_ = ""
    if e.sous_types:
        valeurs = " ".join(f":{t}" for t in e.sous_types)
        r = query(f"SELECT ?t WHERE {{ :{ident} a ?t . VALUES ?t {{ {valeurs} }} }} LIMIT 1")
        type_ = rdf.local(r[0]["t"]["value"]) if r else ""
    champs = champs_pour(e, type_)
    props = " ".join(f":{c.cle}" for c in champs)
    brut = {}
    for r in query(f"SELECT ?p ?o WHERE {{ :{ident} ?p ?o . VALUES ?p {{ {props} }} }}"):
        brut.setdefault(rdf.local(r["p"]["value"]), []).append(r["o"]["value"])
    valeurs = {}
    for c in champs:
        v = brut.get(c.cle, [])
        if c.genre == "relation":
            valeurs[c.cle] = [rdf.local(x) for x in v]
        elif c.genre == "booleen":
            valeurs[c.cle] = bool(v) and v[0] == "true"
        elif c.genre == "date":
            valeurs[c.cle] = v[0][:10] if v else ""
        else:
            valeurs[c.cle] = v[0] if v else ""
    return type_, valeurs


# ---------- Validation ----------
def valider(e, post, type_force=None):
    """Retourne (type, valeurs, erreurs). type_force : type imposé en modification."""
    type_ = type_force if type_force is not None else post.get("type", "")
    if not e.sous_types:
        type_ = ""
    elif type_force is None and type_ not in e.sous_types:
        return type_, {}, ["Choisissez un type."]

    valeurs, erreurs = {}, []
    for c in champs_pour(e, type_):
        if c.genre == "relation":
            autorises = {i for i, _ in rdf.lister_individus(c.cible)}
            choisis = post.getlist(c.cle)
            if any(x not in autorises for x in choisis):
                erreurs.append(f"« {c.libelle} » : valeur inconnue.")
            valeurs[c.cle] = choisis
        elif c.genre == "booleen":
            valeurs[c.cle] = post.get(c.cle) == "on"
        else:
            brut = post.get(c.cle, "").strip()
            valeurs[c.cle] = brut
            if not brut:
                if c.obligatoire:
                    erreurs.append(f"« {c.libelle} » est obligatoire.")
                continue
            if c.genre == "choix" and brut not in c.choix:
                erreurs.append(f"« {c.libelle} » invalide.")
                continue
            try:
                CONVERSION[c.genre](brut)
            except ValueError as err:
                erreurs.append(f"« {c.libelle} » : {err}")
    return type_, valeurs, erreurs


# ---------- Écriture ----------
def _proprietes(e, type_, valeurs):
    props = {}
    for c in champs_pour(e, type_):
        if c.genre == "relation":
            continue
        v = valeurs.get(c.cle)
        if c.genre == "booleen":
            props[c.cle] = rdf.booleen(v)
        else:
            props[c.cle] = CONVERSION[c.genre](v) if v else None
    for prop, sources in e.derives.items():
        props[prop] = next((props[s] for s in sources if props.get(s)), None)
    if e.dates_evenement:
        props["dateEvenement"] = [props[c.cle] for c in champs_pour(e, type_)
                                  if c.genre == "date" and props.get(c.cle)]
    return props


def _relations(e, ident, type_, valeurs, remplacer):
    ops = []
    for c in champs_pour(e, type_):
        if c.genre != "relation":
            continue
        if remplacer:
            # On ne retire que les liens vers la classe visée : les autres liens restent intacts.
            ops.append(f"DELETE {{ :{ident} :{c.cle} ?o }} WHERE {{ :{ident} :{c.cle} ?o . ?o a :{c.cible} }}")
            if c.inverse:
                ops.append(f"DELETE {{ ?o :{c.inverse} :{ident} }} "
                           f"WHERE {{ ?o :{c.inverse} :{ident} . ?o a :{c.cible} }}")
        for cible in valeurs.get(c.cle, []):
            ops.append(f"INSERT DATA {{ :{ident} :{c.cle} :{cible} }}")
            if c.inverse:
                ops.append(f"INSERT DATA {{ :{cible} :{c.inverse} :{ident} }}")
    if ops:
        update(" ;\n".join(ops))


def creer(e, type_, valeurs):
    """Crée l'individu ; retourne son id, ou None s'il existe déjà."""
    if e.cle:
        ident = rdf.fabriquer_id(e.classe, valeurs[e.cle])
    else:
        ident = f"{e.classe}_{uuid.uuid4().hex[:8]}"
    if rdf.existe(ident):
        return None
    classes = [e.classe] + ([type_] if type_ else [])
    rdf.creer(ident, classes, _proprietes(e, type_, valeurs))
    _relations(e, ident, type_, valeurs, remplacer=False)
    return ident


def modifier(e, ident, type_, valeurs):
    rdf.remplacer(ident, _proprietes(e, type_, valeurs))
    _relations(e, ident, type_, valeurs, remplacer=True)


def supprimer(ident):
    rdf.supprimer(ident)


# ---------- Aide au formulaire ----------
def groupes_formulaire(e, valeurs, type_):
    """Groupes de champs pour le template : un groupe commun (code "") + un par sous-type."""
    options = {}

    def opts(cible):
        if cible not in options:
            options[cible] = rdf.lister_individus(cible)
        return options[cible]

    groupes = []
    for code in [""] + list(e.sous_types):
        champs = []
        for c in e.champs:
            if (code == "" and c.pour) or (code != "" and code not in c.pour):
                continue
            actif = code == "" or code == type_
            v = valeurs.get(c.cle) if actif else None
            item = {"cle": c.cle, "libelle": c.libelle, "genre": c.genre,
                    "obligatoire": c.obligatoire, "choix": c.choix, "valeur": v if v is not None else ""}
            if c.genre == "relation":
                choisis = v or []
                item["options"] = [(i, nom, i in choisis) for i, nom in opts(c.cible)]
            champs.append(item)
        if champs:
            groupes.append({"code": code, "champs": champs})
    return groupes
