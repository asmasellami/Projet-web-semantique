from urllib.error import URLError

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .services import contrats, crud, rdf


def liste_contrats(request):
    g = request.GET
    filtres = {k: g.get(k, "").strip() for k in ("q", "type", "statut", "mode", "prime_min", "prime_max")}
    try:
        liste = contrats.lister(filtres["q"], filtres["type"], filtres["statut"], filtres["mode"],
                                filtres["prime_min"], filtres["prime_max"])
    except ValueError as e:
        messages.error(request, f"Filtre invalide : {e}")
        liste = contrats.lister()
    stats = {
        "total": len(liste),
        "actifs": sum(1 for c in liste if c["statut"] == "Actif"),
        "prime_totale": round(sum(float(c["prime"]) for c in liste if c["prime"] != "—"), 2),
    }
    return render(request, "app/contrats_liste.html", {
        "contrats": liste, "f": filtres, "stats": stats,
        "types": contrats.TYPES, "statuts": contrats.STATUTS, "modes": contrats.MODES,
    })


def _formulaire(request, ident=None):
    ancien_type = ""
    if ident:
        rdf.identifiant_valide(ident)
        valeurs = contrats.charger(ident)
        if valeurs is None:
            raise Http404("Contrat introuvable")
        ancien_type = valeurs["type"]
    else:
        valeurs = {"type": "", "numero": "", "statut": "Actif", "prime": "", "date_debut": "",
                   "date_fin": "", "date_signature": "", "mode": "Annuel", "tacite": False, "relations": {}}
    erreurs = []

    if request.method == "POST":
        valeurs, erreurs = contrats.valider(request.POST)
        if not erreurs:
            try:
                if ident:
                    contrats.modifier(ident, valeurs, ancien_type)
                    messages.success(request, f"Contrat {valeurs['numero']} modifié.")
                    return redirect("contrats")
                if contrats.creer(valeurs):
                    messages.success(request, f"Contrat {valeurs['numero']} créé.")
                    return redirect("contrats")
                erreurs.append("Un contrat avec ce numéro existe déjà.")
            except URLError:
                erreurs.append("Fuseki est injoignable (écriture impossible).")

    return render(request, "app/contrat_form.html", {
        "v": valeurs, "erreurs": erreurs,
        "relations": crud.groupes_formulaire(contrats.ENTITE_REL, valeurs.get("relations", {}), "")[0]["champs"], "edition": bool(ident), "ident": ident,
        "types": contrats.TYPES, "statuts": contrats.STATUTS, "modes": contrats.MODES,
    })


def creer_contrat(request):
    return _formulaire(request)


def modifier_contrat(request, ident):
    return _formulaire(request, ident)


@require_POST
def supprimer_contrat(request, ident):
    rdf.identifiant_valide(ident)
    try:
        contrats.supprimer(ident)
        messages.success(request, "Contrat supprimé.")
    except URLError:
        messages.error(request, "Fuseki est injoignable (suppression impossible).")
    return redirect("contrats")
