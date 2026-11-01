"""Module Sinistres : classes Sinistre et Dommage."""
from .crud import Champ, Entite

STATUTS = ("Déclaré", "En expertise", "Indemnisé", "Refusé", "Clôturé")

SINISTRE = Entite(
    slug="sinistres", classe="Sinistre", singulier="sinistre", pluriel="Sinistres", module="sinistres",
    cle="numeroDossier", dates_evenement=True, liste_perso=True,
    sous_types={"Accident": "Accident", "Incendie": "Incendie", "DegatDesEaux": "Dégât des eaux",
                "Vol": "Vol", "CatastropheNaturelle": "Catastrophe naturelle"},
    champs=[
        Champ("numeroDossier", "N° de dossier", "texte", True, liste=True),
        Champ("statutDossier", "Statut", "choix", True, choix=STATUTS, liste=True, filtre=True),
        Champ("dateSinistre", "Date du sinistre", "date", True, liste=True),
        Champ("dateDeclaration", "Date de déclaration", "date"),
        Champ("lieuSinistre", "Lieu", "texte", liste=True),
        Champ("scoreRisqueFraude", "Score de fraude (0 à 1)", "decimal", liste=True),
        Champ("descriptionCirconstances", "Circonstances", "zone"),
        Champ("nombreVehiculesImpliques", "Véhicules impliqués", "entier", pour=("Accident",)),
        Champ("numeroConstatAmiable", "N° de constat amiable", "texte", pour=("Accident",)),
        Champ("origineIncendie", "Origine de l'incendie", "texte", pour=("Incendie",)),
        Champ("concerneContrat", "Contrat concerné", "relation", cible="ContratAssurance",
              inverse="estConcerneParSinistre"),
        Champ("concerneBien", "Bien concerné", "relation", cible="BienAssure"),
        Champ("garantieMobilisable", "Garantie(s) mobilisable(s)", "relation", cible="Garantie"),
        Champ("estEvalueePar", "Expertise(s)", "relation", cible="Expertise"),
        Champ("impliqueAssure", "Assuré(s) impliqué(s)", "relation", cible="Assure", inverse="aConnuSinistre"),
    ],
)

DOMMAGE = Entite(
    slug="dommages", classe="Dommage", singulier="dommage", pluriel="Dommages", module="sinistres",
    champ_montant="montantEstime", derives={"montant": ["montantEstime"]},
    sous_types={"DommageCorporel": "Corporel", "DommageMateriel": "Matériel", "DommageImmateriel": "Immatériel"},
    champs=[
        Champ("descriptionDommage", "Description", "zone", True, liste=True),
        Champ("niveauGravite", "Gravité (1 à 5)", "entier", True, liste=True),
        Champ("montantEstime", "Montant estimé (TND)", "decimal", True, liste=True),
        Champ("estReparable", "Réparable", "booleen", pour=("DommageMateriel",), liste=True),
        Champ("dureeITTJours", "Incapacité temporaire (jours)", "entier", pour=("DommageCorporel",)),
        Champ("tauxIPP", "Taux d'IPP (%)", "decimal", pour=("DommageCorporel",)),
        Champ("resulteDe", "Sinistre à l'origine", "relation", cible="Sinistre", inverse="causeDommage", liste=True),
    ],
)

ENTITES = [SINISTRE, DOMMAGE]
