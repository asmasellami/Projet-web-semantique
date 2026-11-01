"""Module Acteurs : classes Acteur (assurés, experts, bénéficiaires, compagnies) et Expertise."""
from .crud import Champ, Entite

ACTEUR = Entite(
    slug="acteurs", classe="Acteur", singulier="acteur", pluriel="Acteurs", module="acteurs",
    cle="nom", champ_montant="capitalSocial",
    derives={"identifiant": ["cin", "matriculeFiscal", "numeroAgrement", "nom"], "montant": ["capitalSocial"]},
    sous_types={"Assure": "Assuré", "Expert": "Expert", "Beneficiaire": "Bénéficiaire",
                "CompagnieAssurance": "Compagnie d'assurance"},
    champs=[
        Champ("nom", "Nom", "texte", True, liste=True),
        Champ("email", "Email", "texte", liste=True),
        Champ("telephone", "Téléphone", "texte", liste=True),
        Champ("cin", "CIN", "texte", pour=("Assure",), liste=True),
        Champ("profession", "Profession", "texte", pour=("Assure",)),
        Champ("anneesPermis", "Années de permis", "entier", pour=("Assure",)),
        Champ("coefficientBonusMalus", "Coefficient bonus-malus", "decimal", pour=("Assure",)),
        Champ("specialite", "Spécialité", "texte", pour=("Expert",), liste=True),
        Champ("numeroAgrement", "N° d'agrément", "texte", pour=("Expert", "CompagnieAssurance")),
        Champ("lienAvecAssure", "Lien avec l'assuré", "texte", pour=("Beneficiaire",)),
        Champ("matriculeFiscal", "Matricule fiscal", "texte", pour=("CompagnieAssurance",)),
        Champ("capitalSocial", "Capital social (TND)", "decimal", pour=("CompagnieAssurance",)),
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
