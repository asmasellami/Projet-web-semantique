from django.urls import path
from . import views, views_assures, views_biens, views_contrats, views_crud, views_nlp
from .services.registre import REGISTRE

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("sinistres/", views.liste_sinistres, name="sinistres"),

    path("contrats/", views_contrats.liste_contrats, name="contrats"),
    path("contrats/nouveau/", views_contrats.creer_contrat, name="contrat_creer"),
    path("contrats/<str:ident>/modifier/", views_contrats.modifier_contrat, name="contrat_modifier"),
    path("contrats/<str:ident>/supprimer/", views_contrats.supprimer_contrat, name="contrat_supprimer"),

    path("assures/", views_assures.liste_assures, name="assures"),
    path("question/", views_nlp.poser_question, name="question"),

    path("biens/", views_biens.liste_biens, name="biens"),
    path("biens/nouveau/", views_biens.creer_bien, name="bien_creer"),
    path("biens/<str:ident>/modifier/", views_biens.modifier_bien, name="bien_modifier"),
    path("biens/<str:ident>/supprimer/", views_biens.supprimer_bien, name="bien_supprimer"),
]

# Routes générées pour chaque entité du registre : /<slug>/, /<slug>/nouveau/, ...
for e in REGISTRE.values():
    if not e.liste_perso:
        urlpatterns.append(path(f"{e.slug}/", views_crud.liste, {"slug": e.slug}, name=e.slug))
    urlpatterns += [
        path(f"{e.slug}/nouveau/", views_crud.creer, {"slug": e.slug}, name=f"{e.slug}_creer"),
        path(f"{e.slug}/<str:ident>/modifier/", views_crud.modifier, {"slug": e.slug}, name=f"{e.slug}_modifier"),
        path(f"{e.slug}/<str:ident>/supprimer/", views_crud.supprimer, {"slug": e.slug}, name=f"{e.slug}_supprimer"),
    ]
