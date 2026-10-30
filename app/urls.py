from django.urls import path
from . import views, views_biens, views_contrats

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("sinistres/", views.liste_sinistres, name="sinistres"),

    path("contrats/", views_contrats.liste_contrats, name="contrats"),
    path("contrats/nouveau/", views_contrats.creer_contrat, name="contrat_creer"),
    path("contrats/<str:ident>/modifier/", views_contrats.modifier_contrat, name="contrat_modifier"),
    path("contrats/<str:ident>/supprimer/", views_contrats.supprimer_contrat, name="contrat_supprimer"),

    path("biens/", views_biens.liste_biens, name="biens"),
    path("biens/nouveau/", views_biens.creer_bien, name="bien_creer"),
    path("biens/<str:ident>/modifier/", views_biens.modifier_bien, name="bien_modifier"),
    path("biens/<str:ident>/supprimer/", views_biens.supprimer_bien, name="bien_supprimer"),
]
