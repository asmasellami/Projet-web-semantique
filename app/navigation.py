"""Menu latéral : un groupe par module. Chaque membre édite uniquement sa ligne.

Format d'un lien : (libellé, nom de la route). L'icône est un tracé SVG (24x24).
"""
from django.urls import reverse

ICONES = {
    "accueil": "M3 11l9-8 9 8v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z",
    "contrats": "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z M14 3v5h5 M9 13h6 M9 17h6",
    "sinistres": "M10.3 3.9L1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z M12 9v4 M12 17h.01",
    "indemnisation": "M2 7a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2z M2 10h20 M6 15h4",
    "garanties": "M12 2l8 3v6c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11V5z M9 12l2 2 4-4",
    "question": "M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3 M12 17h.01",
    "acteurs": "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2 M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z "
               "M23 21v-2a4 4 0 0 0-3-3.9 M16 3.1a4 4 0 0 1 0 7.8",
}

MODULES = [
    {"nom": "Contrats & Biens", "icone": "contrats",
     "liens": [("Contrats", "contrats"), ("Biens assurés", "biens")]},
    {"nom": "Sinistres", "icone": "sinistres",
     "liens": [("Sinistres", "sinistres"), ("Dommages", "dommages")]},
    {"nom": "Indemnisation", "icone": "indemnisation",
     "liens": [("Indemnisations", "indemnisations"), ("Barèmes", "baremes")]},
    {"nom": "Garanties & Clauses", "icone": "garanties",
     "liens": [("Garanties", "garanties"), ("Clauses", "clauses")]},
    {"nom": "Acteurs & Expertises", "icone": "acteurs",
     "liens": [("Acteurs", "acteurs"), ("Assurés", "assures"), ("Expertises", "expertises")]},
    {"nom": "Assistant NLP", "icone": "question",
     "liens": [("Assistant multilingue", "assistant")]},
]


def navigation(request):
    """Context processor : modules du menu, avec le lien actif repéré par l'URL."""
    modules = []
    for m in MODULES:
        liens = []
        for libelle, route in m["liens"]:
            url = reverse(route)
            liens.append({"libelle": libelle, "url": url, "actif": request.path.startswith(url)})
        modules.append({"nom": m["nom"], "icone": ICONES[m["icone"]], "liens": liens,
                        "actif": any(l["actif"] for l in liens), "url": liens[0]["url"]})
    return {"modules": modules, "icone_accueil": ICONES["accueil"], "accueil_actif": request.path == "/"}
