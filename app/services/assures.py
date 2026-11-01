"""Page « Assurés » : vue de la classe Assure (sous-classe d'Acteur) avec ses relations.

La création, la modification et la suppression passent par le moteur CRUD générique
(entité « acteurs ») : ce service ne fait que la lecture, la recherche et le filtrage.
"""
from app.sparql_service import query
from . import rdf


def compagnies():
    return rdf.lister_individus("CompagnieAssurance")


def cin_en_double():
    """CIN portés par plusieurs individus (le CIN est une clé OWL de Assure : doublon à fusionner)."""
    rows = query("""
        SELECT ?cin (GROUP_CONCAT(STRAFTER(STR(?a), "#"); separator="|") AS ?ids) WHERE {
            ?a a :Assure ; :cin ?cin .
        } GROUP BY ?cin HAVING (COUNT(?a) > 1)
    """)
    return {r["cin"]["value"]: r["ids"]["value"].split("|") for r in rows}


def lister(recherche="", compagnie="", bonus_min="", bonus_max=""):
    filtres = ""
    if recherche:
        r = rdf.texte_filtre(recherche)
        filtres += ('FILTER(CONTAINS(LCASE(CONCAT(STR(?a), " ", COALESCE(?v_nom, ""), " ", COALESCE(?v_cin, ""), " ", '
                    f'COALESCE(?v_email, ""), " ", COALESCE(?v_profession, ""))), LCASE("{r}")))\n')
    if compagnie:
        c = rdf.identifiant_valide(compagnie)
        filtres += (f"FILTER EXISTS {{ {{ :{c} :estAssureurDe ?a }} UNION "
                    f"{{ ?x :estSouscritPar ?a ; :estEmisPar :{c} }} }}\n")
    for valeur, op in ((bonus_min, ">="), (bonus_max, "<=")):
        if valeur:
            filtres += f"FILTER(?v_bonus {op} {rdf.decimal(valeur)})\n"

    rows = query(f"""
        SELECT ?a (SAMPLE(?v_nom) AS ?nom) (SAMPLE(?v_cin) AS ?cin) (SAMPLE(?v_email) AS ?email)
               (SAMPLE(?v_tel) AS ?telephone) (SAMPLE(?v_profession) AS ?profession)
               (SAMPLE(?v_bonus) AS ?bonus)
               (COUNT(DISTINCT ?b) AS ?nbBiens) (COUNT(DISTINCT ?c) AS ?nbContrats)
               (GROUP_CONCAT(DISTINCT ?compNom; separator="|") AS ?compagnies)
        WHERE {{
            ?a a :Assure .
            OPTIONAL {{ ?a :nom ?v_nom }}
            OPTIONAL {{ ?a :cin ?v_cin }}
            OPTIONAL {{ ?a :email ?v_email }}
            OPTIONAL {{ ?a :telephone ?v_tel }}
            OPTIONAL {{ ?a :profession ?v_profession }}
            OPTIONAL {{ ?a :coefficientBonusMalus ?v_bonus }}
            OPTIONAL {{ {{ ?a :estProprietaireDe ?b }} UNION {{ ?b :appartientA ?a }} }}
            OPTIONAL {{ {{ ?a :souscrit ?c }} UNION {{ ?c :estSouscritPar ?a }} }}
            OPTIONAL {{
                {{ ?comp :estAssureurDe ?a }} UNION {{ ?ct :estSouscritPar ?a ; :estEmisPar ?comp }}
                BIND(STRAFTER(STR(?comp), "#") AS ?compNom)
            }}
            {filtres}
        }}
        GROUP BY ?a
        ORDER BY ?nom ?a
    """)
    doublons = cin_en_double()

    assures = []
    for r in rows:
        def val(k):
            return r.get(k, {}).get("value", "")
        ident = rdf.local(val("a"))
        autres = [i for i in doublons.get(val("cin"), []) if i != ident]
        assures.append({
            "id": ident,
            "nom": val("nom") or ident.replace("_", " "),
            "cin": val("cin"),
            "email": val("email"),
            "telephone": val("telephone"),
            "profession": val("profession"),
            "bonus": val("bonus"),
            "nb_biens": int(val("nbBiens") or 0),
            "nb_contrats": int(val("nbContrats") or 0),
            "compagnies": [c.replace("_", " ") for c in val("compagnies").split("|") if c],
            "doublon_de": [i.replace("_", " ") for i in autres],
        })
    return assures
