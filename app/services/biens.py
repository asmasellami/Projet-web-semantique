"""Service BienAssure (Véhicule, Logement, Personne assurée) : recherche, filtrage et CRUD."""
from app.sparql_service import query, update
from . import rdf

TYPES = {"Vehicule": "Véhicule", "Logement": "Logement", "PersonneAssuree": "Personne assurée"}
TYPES_LOGEMENT = ["Appartement", "Maison", "Villa", "Studio"]

# Champs propres à chaque type : (clé du formulaire = propriété, libellé, genre, obligatoire)
CHAMPS = {
    "Vehicule": [
        ("immatriculation", "Immatriculation", "texte", True),
        ("marque", "Marque", "texte", True),
        ("modele", "Modèle", "texte", True),
        ("anneeMiseEnCirculation", "Année de mise en circulation", "entier", False),
        ("puissanceFiscale", "Puissance fiscale (CV)", "entier", False),
        ("valeurVenale", "Valeur vénale (TND)", "decimal", True),
    ],
    "Logement": [
        ("adresse", "Adresse", "texte", True),
        ("typeLogement", "Type de logement", "choix", True),
        ("superficie", "Superficie (m²)", "decimal", False),
        ("nombrePieces", "Nombre de pièces", "entier", False),
        ("valeurDeclaree", "Valeur déclarée (TND)", "decimal", True),
    ],
    "PersonneAssuree": [
        ("numeroAffiliationCNAM", "N° d'affiliation CNAM", "texte", True),
        ("dateNaissance", "Date de naissance", "date", True),
    ],
}
CONVERSION = {"texte": rdf.chaine, "entier": rdf.entier, "decimal": rdf.decimal,
              "date": rdf.date_heure, "choix": rdf.chaine}
# Propriété qui alimente aussi :montant et :identifiant (convention de l'ontologie)
MONTANT = {"Vehicule": "valeurVenale", "Logement": "valeurDeclaree"}
IDENTIFIANT = {"Vehicule": "immatriculation", "PersonneAssuree": "numeroAffiliationCNAM"}
CLE_ID = {"Vehicule": "immatriculation", "Logement": "adresse", "PersonneAssuree": "numeroAffiliationCNAM"}

TOUTES_PROPS = [c[0] for champs in CHAMPS.values() for c in champs]


def proprietaires():
    return rdf.lister_individus("Assure")


def lister(recherche="", type_="", proprietaire="", valeur_min="", valeur_max=""):
    filtres = ""
    if type_ in TYPES:
        filtres += f"?b a :{type_} .\n"
    if recherche:
        r = rdf.texte_filtre(recherche)
        filtres += ('FILTER(CONTAINS(LCASE(CONCAT(STR(?b), " ", COALESCE(?marque, ""), " ", '
                    'COALESCE(?modele, ""), " ", COALESCE(?adresse, ""), " ", '
                    f'COALESCE(?immatriculation, ""))), LCASE("{r}")))\n')
    if proprietaire:
        filtres += f"?b :appartientA :{rdf.identifiant_valide(proprietaire)} .\n"
    for valeur, op in ((valeur_min, ">="), (valeur_max, "<=")):
        if valeur:
            filtres += f"FILTER(COALESCE(?valeurVenale, ?valeurDeclaree) {op} {rdf.decimal(valeur)})\n"

    optionnels = "\n".join(f"OPTIONAL {{ ?b :{p} ?{p} }}" for p in TOUTES_PROPS)
    variables = " ".join(f"?{p}" for p in TOUTES_PROPS)
    rows = query(f"""
        SELECT ?b ?type {variables}
               (GROUP_CONCAT(DISTINCT ?propNom; separator="|") AS ?proprietaires)
        WHERE {{
            ?b a ?type . VALUES ?type {{ :Vehicule :Logement :PersonneAssuree }}
            {optionnels}
            OPTIONAL {{ ?b :appartientA ?p . BIND(STRAFTER(STR(?p), "#") AS ?propNom) }}
            {filtres}
        }}
        GROUP BY ?b ?type {variables}
        ORDER BY ?type ?b
    """)

    biens = []
    for r in rows:
        def val(k):
            return r.get(k, {}).get("value", "")
        t = rdf.local(val("type"))
        if t == "Vehicule":
            titre = f"{val('marque')} {val('modele')}".strip()
            detail = " · ".join(x for x in (val("immatriculation"), val("anneeMiseEnCirculation")) if x)
        elif t == "Logement":
            titre = val("typeLogement") or "Logement"
            detail = " · ".join(x for x in (val("adresse"), f"{val('superficie')} m²" if val("superficie") else "") if x)
        else:
            titre = "Personne assurée"
            detail = " · ".join(x for x in (val("numeroAffiliationCNAM"), val("dateNaissance")[:10]) if x)
        biens.append({
            "id": rdf.local(val("b")),
            "type": TYPES[t],
            "code_type": t,
            "titre": titre,
            "detail": detail,
            "valeur": val("valeurVenale") or val("valeurDeclaree") or "—",
            "proprietaires": [p.replace("_", " ") for p in val("proprietaires").split("|") if p],
        })
    return biens


def charger(ident):
    """(type, valeurs du formulaire, propriétaires) ou None."""
    types = query(f"SELECT ?t WHERE {{ :{ident} a ?t . VALUES ?t {{ :Vehicule :Logement :PersonneAssuree }} }}")
    if not types:
        return None
    t = rdf.local(types[0]["t"]["value"])
    props = " ".join(f":{c[0]}" for c in CHAMPS[t])
    rows = query(f"SELECT ?p ?o WHERE {{ :{ident} ?p ?o . VALUES ?p {{ {props} }} }}")
    valeurs = {rdf.local(r["p"]["value"]): r["o"]["value"] for r in rows}
    if "dateNaissance" in valeurs:
        valeurs["dateNaissance"] = valeurs["dateNaissance"][:10]
    owners = query(f"SELECT ?p WHERE {{ :{ident} :appartientA ?p }}")
    return t, valeurs, [rdf.local(o["p"]["value"]) for o in owners]


def valider(post):
    """Retourne (type, valeurs, propriétaire, erreurs)."""
    t = post.get("type", "")
    erreurs = []
    if t not in TYPES:
        return t, {}, "", ["Choisissez un type de bien."]
    valeurs = {}
    for cle, nom, genre, obligatoire in CHAMPS[t]:
        brut = post.get(cle, "").strip()
        valeurs[cle] = brut
        if not brut:
            if obligatoire:
                erreurs.append(f"« {nom} » est obligatoire.")
            continue
        if genre == "choix" and brut not in TYPES_LOGEMENT:
            erreurs.append(f"« {nom} » invalide.")
            continue
        try:
            CONVERSION[genre](brut)
        except ValueError as e:
            erreurs.append(f"« {nom} » : {e}")
    proprio = post.get("proprietaire", "")
    if proprio and proprio not in dict(proprietaires()):
        erreurs.append("Propriétaire inconnu.")
    return t, valeurs, proprio, erreurs


def _proprietes(t, valeurs):
    props = {c[0]: (CONVERSION[c[2]](valeurs[c[0]]) if valeurs[c[0]] else None) for c in CHAMPS[t]}
    if t in MONTANT:
        props["montant"] = props[MONTANT[t]]
    if t in IDENTIFIANT:
        props["identifiant"] = props[IDENTIFIANT[t]]
    if t == "PersonneAssuree":
        props["dateEvenement"] = props["dateNaissance"]
    return props


def creer(t, valeurs, proprio):
    """Crée le bien ; retourne son id, ou None s'il existe déjà."""
    ident = rdf.fabriquer_id(t, valeurs[CLE_ID[t]])
    if rdf.existe(ident):
        return None
    props = _proprietes(t, valeurs)
    rdf.creer(ident, ["BienAssure", t], props)
    if proprio:
        update(f"INSERT DATA {{ :{ident} :appartientA :{proprio} }}")
    return ident


def modifier(ident, t, valeurs, proprio):
    rdf.remplacer(ident, _proprietes(t, valeurs))
    update(f"DELETE WHERE {{ :{ident} :appartientA ?o }}")
    if proprio:
        update(f"INSERT DATA {{ :{ident} :appartientA :{proprio} }}")


def supprimer(ident):
    rdf.supprimer(ident)
