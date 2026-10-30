"""Service ContratAssurance : recherche, filtrage et CRUD sur Fuseki."""
from app.sparql_service import query
from . import rdf

TYPES = {"ContratAuto": "Auto", "ContratHabitation": "Habitation", "ContratSante": "Santé"}
STATUTS = ["Actif", "Expiré", "Résilié", "Suspendu"]
MODES = ["Annuel", "Semestriel", "Trimestriel", "Mensuel"]


def lister(recherche="", type_="", statut="", mode="", prime_min="", prime_max=""):
    filtres = ""
    if type_ in TYPES:
        filtres += f"?c a :{type_} .\n"
    if recherche:
        r = rdf.texte_filtre(recherche)
        filtres += f'FILTER(CONTAINS(LCASE(CONCAT(?num, " ", STR(?c))), LCASE("{r}")))\n'
    if statut in STATUTS:
        filtres += f"FILTER(?statut = {rdf.chaine(statut)})\n"
    if mode in MODES:
        filtres += f"FILTER(?mode = {rdf.chaine(mode)})\n"
    for valeur, op in ((prime_min, ">="), (prime_max, "<=")):
        if valeur:
            filtres += f"FILTER(?prime {op} {rdf.decimal(valeur)})\n"

    rows = query(f"""
        SELECT ?c ?num ?statut ?prime ?debut ?fin ?mode ?tacite
               (SAMPLE(?t) AS ?type)
               (SAMPLE(?assNom) AS ?assureur)
               (GROUP_CONCAT(DISTINCT ?bienNom; separator="|") AS ?biens)
        WHERE {{
            ?c a :ContratAssurance ; :numeroContrat ?num .
            OPTIONAL {{ ?c :statutContrat ?statut }}
            OPTIONAL {{ ?c :primeAnnuelle ?prime }}
            OPTIONAL {{ ?c :dateDebut ?debut }}
            OPTIONAL {{ ?c :dateFin ?fin }}
            OPTIONAL {{ ?c :modePaiement ?mode }}
            OPTIONAL {{ ?c :renouvellementTacite ?tacite }}
            OPTIONAL {{ ?c a ?t . VALUES ?t {{ :ContratAuto :ContratHabitation :ContratSante }} }}
            OPTIONAL {{ ?c :estEmisPar ?a . BIND(STRAFTER(STR(?a), "#") AS ?assNom) }}
            OPTIONAL {{ ?c :couvreBien ?b . BIND(STRAFTER(STR(?b), "#") AS ?bienNom) }}
            {filtres}
        }}
        GROUP BY ?c ?num ?statut ?prime ?debut ?fin ?mode ?tacite
        ORDER BY DESC(?debut)
    """)

    def val(r, k, defaut=""):
        return r.get(k, {}).get("value", defaut)

    contrats = []
    for r in rows:
        t = rdf.local(val(r, "type"))
        contrats.append({
            "id": rdf.local(r["c"]["value"]),
            "num": r["num"]["value"],
            "type": TYPES.get(t, "—"),
            "statut": val(r, "statut", "—"),
            "prime": val(r, "prime", "—"),
            "debut": val(r, "debut")[:10],
            "fin": val(r, "fin")[:10],
            "mode": val(r, "mode", "—"),
            "tacite": val(r, "tacite") == "true",
            "assureur": val(r, "assureur").replace("_", " ") or "—",
            "biens": [b.replace("_", " ") for b in val(r, "biens").split("|") if b],
        })
    return contrats


def charger(ident):
    """Champs du formulaire pour un contrat existant (None s'il n'existe pas)."""
    if not rdf.existe(ident):
        return None
    rows = query(f"""
        SELECT ?p ?o WHERE {{
            :{ident} ?p ?o .
            VALUES ?p {{ :numeroContrat :statutContrat :primeAnnuelle :dateDebut :dateFin
                         :dateSignature :modePaiement :renouvellementTacite }}
        }}
    """)
    v = {rdf.local(r["p"]["value"]): r["o"]["value"] for r in rows}
    types = query(f"SELECT ?t WHERE {{ :{ident} a ?t . VALUES ?t {{ {' '.join(':' + t for t in TYPES)} }} }}")
    return {
        "type": rdf.local(types[0]["t"]["value"]) if types else "",
        "numero": v.get("numeroContrat", ""),
        "statut": v.get("statutContrat", ""),
        "prime": v.get("primeAnnuelle", ""),
        "date_debut": v.get("dateDebut", "")[:10],
        "date_fin": v.get("dateFin", "")[:10],
        "date_signature": v.get("dateSignature", "")[:10],
        "mode": v.get("modePaiement", ""),
        "tacite": v.get("renouvellementTacite") == "true",
    }


def valider(post):
    """Retourne (valeurs nettoyées, erreurs)."""
    v = {
        "type": post.get("type", ""),
        "numero": post.get("numero", "").strip(),
        "statut": post.get("statut", ""),
        "prime": post.get("prime", "").strip(),
        "date_debut": post.get("date_debut", ""),
        "date_fin": post.get("date_fin", ""),
        "date_signature": post.get("date_signature", ""),
        "mode": post.get("mode", ""),
        "tacite": post.get("tacite") == "on",
    }
    erreurs = []
    if v["type"] not in TYPES:
        erreurs.append("Choisissez un type de contrat.")
    if not v["numero"]:
        erreurs.append("Le numéro de contrat est obligatoire.")
    if v["statut"] not in STATUTS:
        erreurs.append("Statut invalide.")
    if v["mode"] not in MODES:
        erreurs.append("Mode de paiement invalide.")
    try:
        rdf.decimal(v["prime"])
    except ValueError:
        erreurs.append("La prime annuelle doit être un nombre.")
    for cle, nom in (("date_debut", "début"), ("date_fin", "fin")):
        try:
            rdf.date_heure(v[cle])
        except ValueError:
            erreurs.append(f"Date de {nom} invalide.")
    if v["date_signature"]:
        try:
            rdf.date_heure(v["date_signature"])
        except ValueError:
            erreurs.append("Date de signature invalide.")
    if not erreurs and v["date_fin"] < v["date_debut"]:
        erreurs.append("La date de fin doit suivre la date de début.")
    return v, erreurs


def _proprietes(v):
    """Propriétés à écrire ; montant / identifiant / dateEvenement suivent la convention de l'ontologie."""
    prime = rdf.decimal(v["prime"])
    dates = [rdf.date_heure(v["date_debut"]), rdf.date_heure(v["date_fin"])]
    props = {
        "numeroContrat": rdf.chaine(v["numero"]),
        "identifiant": rdf.chaine(v["numero"]),
        "statutContrat": rdf.chaine(v["statut"]),
        "primeAnnuelle": prime,
        "montant": prime,
        "modePaiement": rdf.chaine(v["mode"]),
        "renouvellementTacite": rdf.booleen(v["tacite"]),
        "dateDebut": dates[0],
        "dateFin": dates[1],
        "dateSignature": rdf.date_heure(v["date_signature"]) if v["date_signature"] else None,
    }
    if v["date_signature"]:
        dates.append(props["dateSignature"])
    props["dateEvenement"] = dates
    return props


def creer(v):
    """Crée le contrat ; retourne son id, ou None si le numéro existe déjà."""
    ident = rdf.fabriquer_id("Contrat", v["numero"])
    if rdf.existe(ident):
        return None
    rdf.creer(ident, ["ContratAssurance", v["type"]], _proprietes(v))
    return ident


def modifier(ident, v, ancien_type):
    rdf.remplacer(ident, _proprietes(v))
    if v["type"] != ancien_type:
        from app.sparql_service import update
        retire = f"DELETE DATA {{ :{ident} a :{ancien_type} }} ;\n" if ancien_type in TYPES else ""
        update(retire + f"INSERT DATA {{ :{ident} a :{v['type']} }}")


def supprimer(ident):
    rdf.supprimer(ident)
