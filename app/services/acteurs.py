"""Module Acteurs : classes Acteur (assurés, experts, bénéficiaires, compagnies) et Expertise."""
import re

from app.sparql_service import query
from . import rdf
from .crud import Champ, Entite

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[A-Za-z]{2,}")
_TELEPHONE = re.compile(r"\+?[0-9][0-9 .-]{6,17}[0-9]")
_CIN = re.compile(r"[0-9]{8}")


def verifier_acteur(type_, valeurs, ident):
    """Contrôles métier : formats, et unicité du CIN (axiome OWL HasKey de la classe Assure)."""
    erreurs = []
    if valeurs.get("email") and not _EMAIL.fullmatch(valeurs["email"]):
        erreurs.append("« Email » : adresse invalide (ex. nom@exemple.tn).")
    if valeurs.get("telephone") and not _TELEPHONE.fullmatch(valeurs["telephone"]):
        erreurs.append("« Téléphone » : numéro invalide (ex. +216 98 000 111).")
    cin = valeurs.get("cin", "")
    if type_ == "Assure" and cin:
        if not _CIN.fullmatch(cin):
            erreurs.append("« CIN » : 8 chiffres attendus.")
        elif not ident or not query(f"SELECT ?s WHERE {{ :{rdf.identifiant_valide(ident)} :cin {rdf.chaine(cin)} }}"):
            # Création, ou CIN modifié : on refuse un CIN déjà porté (un doublon historique reste modifiable).
            if query(f"SELECT ?s WHERE {{ ?s :cin {rdf.chaine(cin)} }} LIMIT 1"):
                erreurs.append("« CIN » : un assuré porte déjà ce CIN (le CIN est une clé de la classe Assure).")
    return erreurs


ACTEUR = Entite(
    slug="acteurs", classe="Acteur", singulier="acteur", pluriel="Acteurs", module="acteurs",
    cle="nom", champ_montant="capitalSocial", prefixe_par_type=True, dates_evenement=True,
    verifier=verifier_acteur,
    derives={"identifiant": ["cin", "matriculeFiscal", "numeroAgrement", "nom"], "montant": ["capitalSocial"]},
    sous_types={"Assure": "Assuré", "Expert": "Expert", "Beneficiaire": "Bénéficiaire",
                "CompagnieAssurance": "Compagnie d'assurance"},
    champs=[
        Champ("nom", "Nom", "texte", True, liste=True),
        Champ("email", "Email", "texte", liste=True),
        Champ("telephone", "Téléphone", "texte", liste=True),
        Champ("cin", "CIN", "texte", True, pour=("Assure",), liste=True),
        Champ("dateNaissance", "Date de naissance", "date", pour=("Assure",)),
        Champ("profession", "Profession", "texte", pour=("Assure",)),
        Champ("anneesPermis", "Années de permis", "entier", pour=("Assure",), minimum=0),
        Champ("coefficientBonusMalus", "Coefficient bonus-malus (0,5 à 3,5)", "decimal", pour=("Assure",),
              minimum=0.5, maximum=3.5),
        Champ("estProprietaireDe", "Biens possédés", "relation", cible="BienAssure", inverse="appartientA",
              pour=("Assure",)),
        Champ("estCoAssureAvec", "Co-assuré(s) avec", "relation", cible="Assure", inverse="estCoAssureAvec",
              pour=("Assure",)),
        Champ("specialite", "Spécialité", "texte", pour=("Expert",), liste=True),
        Champ("numeroAgrement", "N° d'agrément", "texte", pour=("Expert", "CompagnieAssurance")),
        Champ("lienAvecAssure", "Lien avec l'assuré", "texte", pour=("Beneficiaire",)),
        Champ("matriculeFiscal", "Matricule fiscal", "texte", pour=("CompagnieAssurance",)),
        Champ("capitalSocial", "Capital social (TND)", "decimal", pour=("CompagnieAssurance",), minimum=0),
        Champ("estReassurePar", "Réassurée par", "relation", cible="CompagnieAssurance",
              pour=("CompagnieAssurance",)),
        Champ("collaboreAvec", "Collabore avec (compagnies)", "relation", cible="CompagnieAssurance",
              pour=("Expert",)),
    ],
)

EXPERTISE = Entite(
    slug="expertises", classe="Expertise", singulier="expertise", pluriel="Expertises", module="acteurs",
    cle="numeroRapport", feminin=True, dates_evenement=True, champ_montant="montantRetenu",
    derives={"identifiant": ["numeroRapport"], "montant": ["montantRetenu"]},
    champs=[
        Champ("numeroRapport", "N° de rapport", "texte", True, liste=True),
        Champ("dateExpertise", "Date de l'expertise", "date", True, liste=True),
        Champ("montantRetenu", "Montant retenu (TND)", "decimal", liste=True),
        Champ("tauxResponsabiliteTiers", "Responsabilité du tiers (%)", "decimal"),
        Champ("estContradictoire", "Contradictoire", "booleen", liste=True),
        Champ("conclusion", "Conclusion", "zone"),
        Champ("realiseePar", "Réalisée par", "relation", cible="Expert", inverse="aRealise", liste=True),
        Champ("mandatePar", "Mandatée par", "relation", cible="CompagnieAssurance"),
        Champ("evalueDommage", "Dommage évalué", "relation", cible="Dommage"),
    ],
)

ENTITES = [ACTEUR, EXPERTISE]
