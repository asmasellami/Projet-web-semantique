"""Vues génériques (liste, création, modification, suppression) pour toutes les entités du registre."""
from urllib.error import URLError

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .services import crud, rdf
from .services.registre import REGISTRE


def _entite(slug):
    if slug not in REGISTRE:
        raise Http404("Entité inconnue")
    return REGISTRE[slug]


def _retour(request, e):
    """Redirection après une action : page d'origine (paramètre next, interne au site) ou liste de l'entité."""
    suivant = request.GET.get("next") or request.POST.get("next") or ""
    if suivant and url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
        return redirect(suivant)
    return redirect(e.slug)


def liste(request, slug):
    e = _entite(slug)
    cles = ["q", "type", "min", "max"] + [c.cle for c in e.champs if c.filtre]
    f = {k: request.GET.get(k, "").strip() for k in cles}
    try:
        lignes, stats = crud.lister(e, f)
    except ValueError as err:
        messages.error(request, f"Filtre invalide : {err}")
        lignes, stats = crud.lister(e, {})
    return render(request, f"app/{e.module}/{e.slug}_liste.html", {
        "e": e, "lignes": lignes, "stats": stats, "f": f,
        "filtres_choix": [{"cle": c.cle, "libelle": c.libelle, "choix": c.choix, "valeur": f[c.cle]}
                          for c in e.champs if c.filtre],
    })


def _formulaire(request, slug, ident=None):
    e = _entite(slug)
    type_, valeurs, erreurs = "", {}, []
    if ident:
        rdf.identifiant_valide(ident)
        charge = crud.charger(e, ident)
        if charge is None:
            raise Http404(f"{e.singulier.capitalize()} introuvable")
        type_, valeurs = charge
    elif request.GET.get("type") in e.sous_types:
        type_ = request.GET["type"]   # lien « Nouvel assuré » : type présélectionné

    if request.method == "POST":
        type_, valeurs, erreurs = crud.valider(e, request.POST, type_force=type_ if ident else None, ident=ident)
        if not erreurs:
            try:
                if ident:
                    crud.modifier(e, ident, type_, valeurs)
                    messages.success(request, f"{e.singulier.capitalize()} {e.modifie}.")
                    return _retour(request, e)
                if crud.creer(e, type_, valeurs):
                    messages.success(request, f"{e.singulier.capitalize()} {e.cree}.")
                    return _retour(request, e)
                erreurs.append("Cet élément existe déjà (même identifiant).")
            except URLError:
                erreurs.append("Fuseki est injoignable (écriture impossible).")

    return render(request, f"app/{e.module}/{e.slug}_form.html", {
        "e": e, "edition": bool(ident), "ident": ident, "type": type_, "erreurs": erreurs,
        "groupes": crud.groupes_formulaire(e, valeurs, type_),
    })


def creer(request, slug):
    return _formulaire(request, slug)


def modifier(request, slug, ident):
    return _formulaire(request, slug, ident)


@require_POST
def supprimer(request, slug, ident):
    e = _entite(slug)
    rdf.identifiant_valide(ident)
    try:
        crud.supprimer(ident)
        messages.success(request, f"{e.singulier.capitalize()} {e.supprime}.")
    except URLError:
        messages.error(request, "Fuseki est injoignable (suppression impossible).")
    return _retour(request, e)
