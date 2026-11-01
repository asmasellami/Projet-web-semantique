"""Module Indemnisation : classes Indemnisation et BaremeIndemnisation."""
from .crud import Champ, Entite

INDEMNISATION = Entite(
    slug="indemnisations", classe="Indemnisation", singulier="indemnisation", pluriel="Indemnisations",
    module="indemnisation", cle="referencePaiement", feminin=True, dates_evenement=True,
    champ_montant="montantVerse", derives={"identifiant": ["referencePaiement"]},
    champs=[
        Champ("referencePaiement", "Référence de paiement", "texte", True, liste=True),
        Champ("dateVersement", "Date de versement", "date", True, liste=True),
        Champ("montantVerse", "Montant versé (TND)", "decimal", True, liste=True),
        Champ("franchiseDeduite", "Franchise déduite (TND)", "decimal", liste=True),
        Champ("modeReglement", "Mode de règlement", "choix", choix=("Virement", "Chèque", "Espèces"),
              liste=True, filtre=True),
        Champ("indemniseSinistre", "Sinistre indemnisé", "relation", cible="Sinistre",
              inverse="donneLieuA", liste=True),
        Champ("mobiliseGarantie", "Garantie mobilisée", "relation", cible="Garantie"),
        Champ("estCalculeeSelon", "Barème appliqué", "relation", cible="BaremeIndemnisation"),
        Champ("appliqueFranchise", "Franchise appliquée", "relation", cible="ClauseFranchise"),
        Champ("estPayeePar", "Payée par", "relation", cible="CompagnieAssurance"),
        Champ("estVerseeA", "Versée à", "relation", cible="Acteur"),
    ],
)

BAREME = Entite(
    slug="baremes", classe="BaremeIndemnisation", singulier="barème", pluriel="Barèmes d'indemnisation",
    module="indemnisation", cle="referenceBareme", dates_evenement=True, champ_montant="plafondBareme",
    derives={"identifiant": ["referenceBareme"], "montant": ["montantForfait"]},
    sous_types={"BaremeForfaitaire": "Forfaitaire", "BaremeProportionnel": "Proportionnel"},
    champs=[
        Champ("referenceBareme", "Référence", "texte", True, liste=True),
        Champ("dateEffet", "Date d'effet", "date", True, liste=True),
        Champ("plafondBareme", "Plafond (TND)", "decimal", liste=True),
        Champ("montantForfait", "Montant forfaitaire (TND)", "decimal", pour=("BaremeForfaitaire",), liste=True),
        Champ("tauxRemboursement", "Taux de remboursement (0 à 1)", "decimal",
              pour=("BaremeProportionnel",), liste=True),
    ],
)

ENTITES = [INDEMNISATION, BAREME]
