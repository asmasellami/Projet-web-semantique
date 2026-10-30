from urllib.error import URLError

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .services import biens, rdf


def liste_biens(request):
    g = request.GET
    filtres = {k: g.get(k, "").strip() for k in ("q", "type", "proprietaire", "valeur_min", "valeur_max")}
    try:
        liste = biens.lister(**{("recherche" if k == "q" else "type_" if k == "type" else k): v
                                for k, v in filtres.items()})
    except (ValueError, Http404) as e:
        messages.error(request, f"Filtre invalide : {e}")
        liste = biens.lister()
    stats = {
        "total": len(liste),
        "vehicules": sum(1 for b in liste if b["code_type"] == "Vehicule"),
        "logements": sum(1 for b in liste if b["code_type"] == "Logement"),
        "personnes": sum(1 for b in liste if b["code_type"] == "PersonneAssuree"),
    }
    return render(request, "app/biens_liste.html", {
        "biens": liste, "f": filtres, "stats": stats,
        "types": biens.TYPES, "proprietaires": biens.proprietaires(),
    })


def _formulaire(request, ident=None):
    type_, valeurs, proprio = "", {}, ""
    if ident:
        rdf.identifiant_valide(ident)
        charge = biens.charger(ident)
        if charge is None:
            raise Http404("Bien introuvable")
        type_, valeurs, owners = charge
        proprio = owners[0] if owners else ""
    erreurs = []

    if request.method == "POST":
        if ident:
            request.POST = request.POST.copy()
            request.POST["type"] = type_  # le type ne change pas en édition
        type_, valeurs, proprio, erreurs = biens.valider(request.POST)
        if not erreurs:
            try:
                if ident:
                    biens.modifier(ident, type_, valeurs, proprio)
                    messages.success(request, "Bien modifié.")
                    return redirect("biens")
                if biens.creer(type_, valeurs, proprio):
                    messages.success(request, "Bien créé.")
                    return redirect("biens")
                erreurs.append("Ce bien existe déjà.")
            except URLError:
                erreurs.append("Fuseki est injoignable (écriture impossible).")

    groupes = [{
        "code": code,
        "champs": [{"cle": cle, "nom": nom, "genre": genre, "obligatoire": oblig,
                    "valeur": valeurs.get(cle, "") if code == type_ else ""}
                   for cle, nom, genre, oblig in biens.CHAMPS[code]],
    } for code in biens.TYPES]

    return render(request, "app/bien_form.html", {
        "type": type_, "proprio": proprio, "erreurs": erreurs,
        "edition": bool(ident), "ident": ident,
        "types": biens.TYPES, "groupes": groupes, "types_logement": biens.TYPES_LOGEMENT,
        "proprietaires": biens.proprietaires(),
    })


def creer_bien(request):
    return _formulaire(request)


def modifier_bien(request, ident):
    return _formulaire(request, ident)


@require_POST
def supprimer_bien(request, ident):
    rdf.identifiant_valide(ident)
    try:
        biens.supprimer(ident)
        messages.success(request, "Bien supprimé.")
    except URLError:
        messages.error(request, "Fuseki est injoignable (suppression impossible).")
    return redirect("biens")
