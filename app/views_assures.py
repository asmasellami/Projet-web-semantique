from django.contrib import messages
from django.http import Http404
from django.shortcuts import render

from .services import assures


def liste_assures(request):
    g = request.GET
    f = {k: g.get(k, "").strip() for k in ("q", "compagnie", "bonus_min", "bonus_max")}
    try:
        liste = assures.lister(recherche=f["q"], compagnie=f["compagnie"],
                               bonus_min=f["bonus_min"], bonus_max=f["bonus_max"])
    except (ValueError, Http404) as e:
        messages.error(request, f"Filtre invalide : {e}")
        liste = assures.lister()
    stats = {
        "total": len(liste),
        "avec_contrat": sum(1 for a in liste if a["nb_contrats"]),
        "biens": sum(a["nb_biens"] for a in liste),
        "doublons": sum(1 for a in liste if a["doublon_de"]),
    }
    return render(request, "app/assures_liste.html", {
        "assures": liste, "f": f, "stats": stats, "compagnies": assures.compagnies(),
    })
