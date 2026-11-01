"""Page « Poser une question » : question en français -> analyse spaCy -> SPARQL -> résultats."""
from django.shortcuts import render

from . import nlp


def poser_question(request):
    reponse, candidats = None, []
    if "q" in request.GET:
        reponse = nlp.repondre(request.GET.get("q", ""), entite=request.GET.get("entite", "").strip())
        if reponse.statut == "ambigue":
            candidats = [{"libelle": g[0].libelle, "ids": ",".join(e.id for e in g),
                          "details": ", ".join(e.id for e in g)} for g in reponse.resolution.groupes]
    return render(request, "app/question.html", {
        "q": request.GET.get("q", ""),
        "rep": reponse,
        "candidats": candidats,
        "intentions": list(nlp.INTENTIONS.values()),
    })
