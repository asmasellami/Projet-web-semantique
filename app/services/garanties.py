"""Module Garanties : classes Garantie et Clause."""
from .crud import Champ, Entite

GARANTIE = Entite(
    slug="garanties", classe="Garantie", singulier="garantie", pluriel="Garanties", module="garanties",
    cle="codeGarantie", feminin=True, champ_montant="plafondGarantie",
    derives={"identifiant": ["codeGarantie"], "montant": ["plafondGarantie"]},
    sous_types={"GarantieResponsabiliteCivile": "Responsabilité civile", "GarantieVol": "Vol",
                "GarantieIncendie": "Incendie", "GarantieDegatsDesEaux": "Dégâts des eaux",
                "GarantieBrisDeGlace": "Bris de glace", "GarantieHospitalisation": "Hospitalisation"},
    champs=[
        Champ("codeGarantie", "Code", "texte", True, liste=True),
        Champ("plafondGarantie", "Plafond (TND)", "decimal", True, liste=True),
        Champ("delaiCarenceJours", "Délai de carence (jours)", "entier", liste=True),
        Champ("estObligatoire", "Obligatoire", "booleen", liste=True),
        Champ("appliqueBareme", "Barème appliqué", "relation", cible="BaremeIndemnisation", liste=True),
    ],
)

CLAUSE = Entite(
    slug="clauses", classe="Clause", singulier="clause", pluriel="Clauses", module="garanties",
    feminin=True, champ_montant="montantFranchise", derives={"montant": ["montantFranchise"]},
    sous_types={"ClauseFranchise": "Franchise", "ClauseExclusion": "Exclusion", "ClauseResiliation": "Résiliation"},
    champs=[
        Champ("texteClause", "Texte de la clause", "zone", True, liste=True),
        Champ("referenceJuridique", "Référence juridique", "texte", liste=True),
        Champ("montantFranchise", "Montant de la franchise (TND)", "decimal",
              pour=("ClauseFranchise",), liste=True),
        Champ("typeFranchise", "Type de franchise", "choix", choix=("Absolue", "Relative"),
              pour=("ClauseFranchise",), liste=True, filtre=True),
        Champ("delaiPreavisJours", "Préavis (jours)", "entier", pour=("ClauseResiliation",)),
        Champ("limiteGarantie", "Garantie limitée", "relation", cible="Garantie", pour=("ClauseFranchise",)),
        Champ("exclutGarantie", "Garantie exclue", "relation", cible="Garantie", pour=("ClauseExclusion",)),
    ],
)

ENTITES = [GARANTIE, CLAUSE]
