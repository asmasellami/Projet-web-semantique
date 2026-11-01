"""Service BienAssure (Véhicule, Logement, Personne assurée) : recherche, filtrage et CRUD.

Les propriétés et contraintes viennent de l'ontologie `assurance_inferee.owl` :
- appartientA (BienAssure -> Assure), inverse estProprietaireDe ;
- couvreBien (ContratAssurance -> BienAssure) ;
- Vehicule : clé OWL (HasKey) = immatriculation ;
- typeLogement : énumération {Appartement, Duplex, Studio, Villa} ;
- facettes de datatype : anneeMiseEnCirculation >= 1950, puissanceFiscale 1..50,
  nombrePieces >= 1, superficie > 0, montant >= 0.
"""
from datetime import date
from decimal import Decimal

from app.sparql_service import query, update
from . import rdf

TYPES = {"Vehicule": "Véhicule", "Logement": "Logement", "PersonneAssuree": "Personne assurée"}
TYPES_LOGEMENT = ["Appartement", "Duplex", "Studio", "Villa"]   # owl:oneOf de typeLogement

# Champs propres à chaque type : (clé du formulaire = propriété, libellé, genre, obligatoire)
CHAMPS = {
    "Vehicule": [
        ("immatriculation", "Immatriculation", "texte", True),
        ("marque", "Marque", "texte", True),
        ("modele", "Modèle", "texte", True),
        ("anneeMiseEnCirculation", "Année de mise en circulation (≥ 1950)", "entier", False),
        ("puissanceFiscale", "Puissance fiscale (1 à 50 CV)", "entier", False),
        ("valeurVenale", "Valeur vénale (TND)", "decimal", True),
    ],
    "Logement": [
        ("adresse", "Adresse", "texte", True),
        ("typeLogement", "Type de logement", "choix", True),
        ("superficie", "Superficie (m², > 0)", "decimal", False),
        ("nombrePieces", "Nombre de pièces (≥ 1)", "entier", False),
        ("valeurDeclaree", "Valeur déclarée (TND)", "decimal", True),
    ],
    "PersonneAssuree": [
        ("numeroAffiliationCNAM", "N° d'affiliation CNAM", "texte", True),
        ("dateNaissance", "Date de naissance", "date", True),
    ],
}
CONVERSION = {"texte": rdf.chaine, "entier": rdf.entier, "decimal": rdf.decimal,
              "date": rdf.date_heure, "choix": rdf.chaine}
# Bornes issues des facettes OWL : propriété -> (minimum, maximum, minimum exclu ?)
BORNES = {
    "anneeMiseEnCirculation": (1950, None, False),
    "puissanceFiscale": (1, 50, False),
    "nombrePieces": (1, None, False),
    "superficie": (0, None, True),
    "valeurVenale": (0, None, False),
    "valeurDeclaree": (0, None, False),
}
# Propriété qui alimente aussi :montant et :identifiant (convention de l'ontologie)
MONTANT = {"Vehicule": "valeurVenale", "Logement": "valeurDeclaree"}
IDENTIFIANT = {"Vehicule": "immatriculation", "PersonneAssuree": "numeroAffiliationCNAM"}
CLE_ID = {"Vehicule": "immatriculation", "Logement": "adresse", "PersonneAssuree": "numeroAffiliationCNAM"}
# Propriétés servant de clé métier : un seul bien du même type par valeur.
CLE_METIER = {"Vehicule": "immatriculation", "PersonneAssuree": "numeroAffiliationCNAM"}

TOUTES_PROPS = [c[0] for champs in CHAMPS.values() for c in champs]


def proprietaires():
    return rdf.lister_individus("Assure")


def contrats():
    return rdf.lister_individus("ContratAssurance")


def lister(recherche="", type_="", proprietaire="", valeur_min="", valeur_max=""):
    filtres = ""
    if type_ in TYPES:
        filtres += f"?b a :{type_} .\n"
    if recherche:
        r = rdf.texte_filtre(recherche)
        filtres += ('FILTER(CONTAINS(LCASE(CONCAT(STR(?b), " ", COALESCE(?marque, ""), " ", '
                    'COALESCE(?modele, ""), " ", COALESCE(?adresse, ""), " ", '
                    'COALESCE(?typeLogement, ""), " ", COALESCE(?numeroAffiliationCNAM, ""), " ", '
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
               (GROUP_CONCAT(DISTINCT ?contratNom; separator="|") AS ?contrats)
        WHERE {{
            ?b a ?type . VALUES ?type {{ :Vehicule :Logement :PersonneAssuree }}
            {optionnels}
            OPTIONAL {{ ?b :appartientA ?p . BIND(STRAFTER(STR(?p), "#") AS ?propNom) }}
            OPTIONAL {{ ?ct :couvreBien ?b . BIND(STRAFTER(STR(?ct), "#") AS ?contratNom) }}
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
            "contrats": [c.replace("_", " ") for c in val("contrats").split("|") if c],
        })
    return biens


def charger(ident):
    """(type, valeurs du formulaire, propriétaires, contrats couvrants) ou None."""
    types = query(f"SELECT ?t WHERE {{ :{ident} a ?t . VALUES ?t {{ :Vehicule :Logement :PersonneAssuree }} }}")
    if not types:
        return None
    t = rdf.local(types[0]["t"]["value"])
    props = " ".join(f":{c[0]}" for c in CHAMPS[t])
    rows = query(f"SELECT ?p ?o WHERE {{ :{ident} ?p ?o . VALUES ?p {{ {props} }} }}")
    valeurs = {rdf.local(r["p"]["value"]): r["o"]["value"] for r in rows}
    if "dateNaissance" in valeurs:
        valeurs["dateNaissance"] = valeurs["dateNaissance"][:10]
    owners = query(f"SELECT ?p WHERE {{ :{ident} :appartientA ?p }} ORDER BY ?p")
    couvrants = query(f"SELECT ?c WHERE {{ ?c :couvreBien :{ident} }} ORDER BY ?c")
    return (t, valeurs, [rdf.local(o["p"]["value"]) for o in owners],
            [rdf.local(c["c"]["value"]) for c in couvrants])


def _hors_bornes(cle, nom, brut):
    minimum, maximum, exclu = BORNES[cle]
    n = Decimal(brut.replace(",", "."))
    if minimum is not None and (n <= minimum if exclu else n < minimum):
        return f"« {nom} » doit être {'strictement supérieur' if exclu else 'supérieur ou égal'} à {minimum}."
    if maximum is not None and n > maximum:
        return f"« {nom} » doit être inférieur ou égal à {maximum}."
    return None


def _cle_deja_prise(t, valeur, ident):
    """Clé métier (HasKey OWL) déjà portée par un autre bien ? Espaces ignorés (« 123 TU 4567 » = « 123TU4567 »)."""
    cle = CLE_METIER[t]
    autre = f"FILTER(?x != :{ident})" if ident else ""
    compact = valeur.replace(" ", "")
    return bool(query(f"""
        SELECT ?x WHERE {{
            ?x a :{t} ; :{cle} ?k .
            FILTER(REPLACE(STR(?k), " ", "") = {rdf.chaine(compact)})
            {autre}
        }} LIMIT 1"""))


def valider(post, ident=None):
    """Retourne (type, valeurs, propriétaires, contrats, erreurs)."""
    t = post.get("type", "")
    erreurs = []
    if t not in TYPES:
        return t, {}, [], [], ["Choisissez un type de bien."]
    valeurs = {}
    for cle, nom, genre, obligatoire in CHAMPS[t]:
        brut = post.get(cle, "").strip()
        valeurs[cle] = brut
        if not brut:
            if obligatoire:
                erreurs.append(f"« {nom} » est obligatoire.")
            continue
        if genre == "choix" and brut not in TYPES_LOGEMENT:
            erreurs.append(f"« {nom} » invalide (valeurs de l'ontologie : {', '.join(TYPES_LOGEMENT)}).")
            continue
        try:
            CONVERSION[genre](brut)
        except ValueError as e:
            erreurs.append(f"« {nom} » : {e}")
            continue
        if cle in BORNES and (hors := _hors_bornes(cle, nom, brut)):
            erreurs.append(hors)
        if cle == "anneeMiseEnCirculation" and int(brut) > date.today().year + 1:
            erreurs.append(f"« {nom} » : année dans le futur.")
        if cle == "dateNaissance" and brut > date.today().isoformat():
            erreurs.append(f"« {nom} » : la date ne peut pas être dans le futur.")
    cle_metier = CLE_METIER.get(t)
    if cle_metier and valeurs.get(cle_metier) and not erreurs and _cle_deja_prise(t, valeurs[cle_metier], ident):
        erreurs.append(f"Un bien de ce type porte déjà cette valeur de « {cle_metier} » (clé OWL).")

    proprios = post.getlist("proprietaire") if hasattr(post, "getlist") else [post.get("proprietaire", "")]
    proprios = [p for p in proprios if p]
    if any(p not in dict(proprietaires()) for p in proprios):
        erreurs.append("Propriétaire inconnu.")
    liens = post.getlist("contrats") if hasattr(post, "getlist") else []
    if any(c not in dict(contrats()) for c in liens):
        erreurs.append("Contrat inconnu.")
    return t, valeurs, proprios, liens, erreurs


def _proprietes(t, valeurs):
    props = {c[0]: (CONVERSION[c[2]](valeurs[c[0]]) if valeurs[c[0]] else None) for c in CHAMPS[t]}
    if t in MONTANT:
        props["montant"] = props[MONTANT[t]]
    if t in IDENTIFIANT:
        props["identifiant"] = props[IDENTIFIANT[t]]
    if t == "PersonneAssuree":
        props["dateEvenement"] = props["dateNaissance"]
    return props


def _ecrire_liens(ident, proprios, liens, remplacer):
    """Relations du bien : propriétaires (avec l'inverse estProprietaireDe) et contrats couvrants."""
    ops = []
    if remplacer:
        ops += [f"DELETE WHERE {{ :{ident} :appartientA ?o }}",
                f"DELETE WHERE {{ ?o :estProprietaireDe :{ident} }}",
                f"DELETE WHERE {{ ?c :couvreBien :{ident} }}"]
    for p in proprios:
        ops += [f"INSERT DATA {{ :{ident} :appartientA :{p} }}",
                f"INSERT DATA {{ :{p} :estProprietaireDe :{ident} }}"]
    ops += [f"INSERT DATA {{ :{c} :couvreBien :{ident} }}" for c in liens]
    if ops:
        update(" ;\n".join(ops))


def creer(t, valeurs, proprios, liens=()):
    """Crée le bien ; retourne son id, ou None s'il existe déjà."""
    ident = rdf.fabriquer_id(t, valeurs[CLE_ID[t]])
    if rdf.existe(ident):
        return None
    rdf.creer(ident, ["BienAssure", t], _proprietes(t, valeurs))
    _ecrire_liens(ident, proprios, liens, remplacer=False)
    return ident


def modifier(ident, t, valeurs, proprios, liens=()):
    rdf.remplacer(ident, _proprietes(t, valeurs))
    _ecrire_liens(ident, proprios, liens, remplacer=True)


def supprimer(ident):
    rdf.supprimer(ident)
