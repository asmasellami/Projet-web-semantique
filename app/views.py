from django.shortcuts import render
from .services import stats as stats_service
from .sparql_service import query

TYPES_SINISTRE = [
    ("Accident", "Accident"),
    ("Incendie", "Incendie"),
    ("DegatDesEaux", "Dégât des eaux"),
    ("Vol", "Vol"),
    ("CatastropheNaturelle", "Catastrophe naturelle"),
]
LIBELLES_TYPES = dict(TYPES_SINISTRE)

LIBELLES_CATEGORIES = {
    "SinistreIndemnise": "Indemnisé",
    "SinistreExpertise": "Expertisé",
    "SinistreCorporel": "Corporel",
}

STATUTS = ["Déclaré", "En expertise", "Indemnisé", "Refusé", "Clôturé"]


# Page de chaque classe racine, quand elle existe : "NomDeLaClasse": "nom_de_l_url".
PAGES_CLASSES = {
    "Sinistre": "sinistres",
    "ContratAssurance": "contrats",
    "BienAssure": "biens",
}


def accueil(request):
    return render(request, "app/accueil.html", {
        "totaux": stats_service.totaux(),
        "classes": [{**c, "url": PAGES_CLASSES.get(c["nom"])} for c in stats_service.repartition()],
    })


def niveau_score(score):
    if score >= 0.5:
        return "eleve"
    if score >= 0.2:
        return "moyen"
    return "faible"


def liste_sinistres(request):
    statut = request.GET.get("statut", "")
    lieu = request.GET.get("lieu", "").replace('"', "")
    type_choisi = request.GET.get("type", "")

    filtres = ""
    if statut in STATUTS:
        filtres += f'FILTER(?statut = "{statut}")\n'
    if lieu:
        filtres += f'FILTER(CONTAINS(LCASE(?lieu), LCASE("{lieu}")))\n'
    if type_choisi in LIBELLES_TYPES:
        filtres += f"FILTER(?type = :{type_choisi})\n"

    rows = query(f"""
        SELECT ?num ?type ?statut ?lieu ?date ?score
               (GROUP_CONCAT(DISTINCT ?catName; separator=",") AS ?categories)
        WHERE {{
            ?s :numeroDossier ?num ;
               :statutDossier ?statut ;
               :lieuSinistre ?lieu ;
               :dateSinistre ?date ;
               :scoreRisqueFraude ?score ;
               a ?type .
            VALUES ?type {{ :Accident :Incendie :DegatDesEaux :Vol :CatastropheNaturelle }}
            OPTIONAL {{
                ?s a ?cat .
                VALUES ?cat {{ :SinistreIndemnise :SinistreExpertise :SinistreCorporel }}
                BIND(STRAFTER(STR(?cat), "#") AS ?catName)
            }}
            {filtres}
        }}
        GROUP BY ?num ?type ?statut ?lieu ?date ?score
        ORDER BY DESC(?date)
    """)

    sinistres = []
    for r in rows:
        code_type = r["type"]["value"].split("#")[-1]
        cats = r.get("categories", {}).get("value", "")
        score = float(r["score"]["value"])
        sinistres.append({
            "num": r["num"]["value"],
            "type": LIBELLES_TYPES.get(code_type, code_type),
            "statut": r["statut"]["value"],
            "lieu": r["lieu"]["value"],
            "date": r["date"]["value"][:10],
            "score": score,
            "niveau_score": niveau_score(score),
            "categories": [LIBELLES_CATEGORIES.get(c, c) for c in cats.split(",") if c],
        })

    total = len(sinistres)
    stats = {
        "total": total,
        "en_expertise": sum(1 for s in sinistres if s["statut"] == "En expertise"),
        "indemnises": sum(1 for s in sinistres if s["statut"] == "Indemnisé"),
        "score_moyen": round(sum(s["score"] for s in sinistres) / total, 2) if total else "—",
    }

    return render(request, "app/sinistres.html", {
        "sinistres": sinistres,
        "stats": stats,
        "statut": statut,
        "lieu": lieu,
        "type_choisi": type_choisi,
        "statuts": STATUTS,
        "types": TYPES_SINISTRE,
    })
