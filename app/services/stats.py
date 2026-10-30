"""Statistiques globales de l'ontologie pour la page d'accueil."""
from app.sparql_service import query
from .rdf import local

NS = "FILTER(STRSTARTS(STR(?x), STR(:)))"


def totaux():
    r = query(f"""
        SELECT ?classes ?sous_classes ?individus ?obj ?data WHERE {{
            {{ SELECT (COUNT(DISTINCT ?x) AS ?classes) WHERE {{ ?x a owl:Class . {NS} }} }}
            {{ SELECT (COUNT(DISTINCT ?x) AS ?sous_classes) WHERE {{
                ?x rdfs:subClassOf ?p . ?p a owl:Class . {NS} FILTER(STRSTARTS(STR(?p), STR(:))) }} }}
            {{ SELECT (COUNT(DISTINCT ?x) AS ?individus) WHERE {{ ?x a owl:NamedIndividual . {NS} }} }}
            {{ SELECT (COUNT(DISTINCT ?x) AS ?obj) WHERE {{ ?x a owl:ObjectProperty . {NS} }} }}
            {{ SELECT (COUNT(DISTINCT ?x) AS ?data) WHERE {{ ?x a owl:DatatypeProperty . {NS} }} }}
        }}
    """)[0]
    return {
        "classes": int(r["classes"]["value"]),
        "sous_classes": int(r["sous_classes"]["value"]),
        "individus": int(r["individus"]["value"]),
        "proprietes_objet": int(r["obj"]["value"]),
        "proprietes_donnees": int(r["data"]["value"]),
    }


def repartition():
    """Classes racines avec leur nombre de sous-classes et d'individus (sous-classes comprises)."""
    rows = query("""
        SELECT ?c (COUNT(DISTINCT ?i) AS ?individus) (COUNT(DISTINCT ?sub) AS ?sous)
        WHERE {
            ?c a owl:Class .
            FILTER(STRSTARTS(STR(?c), STR(:)))
            FILTER NOT EXISTS { ?c rdfs:subClassOf ?p . FILTER(STRSTARTS(STR(?p), STR(:))) }
            OPTIONAL { ?i a ?c . FILTER(STRSTARTS(STR(?i), STR(:))) }
            OPTIONAL { ?sub rdfs:subClassOf+ ?c . FILTER(isIRI(?sub)) }
        }
        GROUP BY ?c
        ORDER BY DESC(?individus) ?c
    """)
    classes = [{
        "nom": local(r["c"]["value"]),
        "individus": int(r["individus"]["value"]),
        "sous": int(r["sous"]["value"]),
    } for r in rows]
    maxi = max((c["individus"] for c in classes), default=0) or 1
    for c in classes:
        c["pct"] = round(100 * c["individus"] / maxi)
    return classes
