"""Intentions NLP du membre 3 (classes Acteur et BienAssure).

1. biens_assure     : « Quels sont les biens assurés de Ahmed ? »
2. assures_compagnie : « Quels sont les assurés de AssurTunis ? »

Les propriétés viennent de l'ontologie : estProprietaireDe / appartientA (inverses), estSouscritPar,
couvreBien, estEmisPar / emet, estAssureurDe (propriété inférée par HermiT : chaîne emet ∘ estSouscritPar).
Les requêtes combinent le chemin explicite par les contrats ET la propriété inférée : elles restent
correctes pour un assuré ajouté depuis l'application (Fuseki ne lance pas HermiT).
"""
from . import nlp

# ---------- Mots déclencheurs (comparés sans accents, aux formes ET aux lemmes) ----------
BIENS = {"bien", "biens", "vehicule", "vehicules", "voiture", "voitures", "auto", "autos", "logement",
         "logements", "maison", "maisons", "appartement", "appartements", "patrimoine", "propriete", "proprietes"}
BIENS_FAIBLES = {"appartenir", "appartenant", "appartient", "appartiennent", "posseder", "possede",
                 "possedent", "possedant", "proprietaire"}
ASSURES = {"assure", "assures", "assuree", "assurees", "assurer", "client", "clients", "souscripteur",
           "souscripteurs", "adherent", "adherents"}
COMPAGNIES = {"compagnie", "compagnies", "assureur", "assureurs", "societe", "agence", "assurance", "assurances"}
AUPRES = {"aupres", "chez"}


def score_biens(ctx):
    fort, a = nlp.cherche(ctx, BIENS, 3)
    faible, b = nlp.cherche(ctx, BIENS_FAIBLES, 1)
    return fort + faible, a + b


def score_assures(ctx):
    # « assurés » juste après « biens » qualifie les biens : ce n'est pas la question sur les assurés.
    fort, a = nlp.cherche(ctx, ASSURES, 2, sauf_apres=BIENS)
    mot, b = nlp.cherche(ctx, COMPAGNIES, 1)
    prep, c = nlp.cherche(ctx, AUPRES, 1)
    return fort + mot + prep, a + b + c


# ---------- Référentiels ----------
def acteurs():
    return nlp.charger_entites("Acteur", ("Assure", "CompagnieAssurance", "Expert", "Beneficiaire"))


# ---------- Templates SPARQL (seuls des identifiants d'individus validés y sont insérés) ----------
def requete_biens(ids):
    valeurs = " ".join(f":{i}" for i in ids)
    return f"""SELECT ?bien ?type
       (SAMPLE(?descr) AS ?description) (SAMPLE(?val) AS ?valeur)
       (GROUP_CONCAT(DISTINCT ?lien; separator=" ; ") AS ?liens)
       (GROUP_CONCAT(DISTINCT ?numContrat; separator=", ") AS ?contrats)
WHERE {{
  VALUES ?assure {{ {valeurs} }}
  {{ ?assure :estProprietaireDe ?bien . BIND("propriétaire" AS ?lien) }}
  UNION {{ ?bien :appartientA ?assure . BIND("propriétaire" AS ?lien) }}
  UNION {{ ?contrat :estSouscritPar ?assure ; :couvreBien ?bien .
           BIND("couvert par un contrat de l'assuré" AS ?lien) }}
  ?bien a ?type . VALUES ?type {{ :Vehicule :Logement :PersonneAssuree }}
  OPTIONAL {{ ?ctr :estSouscritPar ?assure ; :couvreBien ?bien ; :numeroContrat ?numContrat }}
  OPTIONAL {{ ?bien :marque ?marque }} OPTIONAL {{ ?bien :modele ?modele }}
  OPTIONAL {{ ?bien :immatriculation ?immat }}
  OPTIONAL {{ ?bien :typeLogement ?tl }} OPTIONAL {{ ?bien :adresse ?adresse }}
  OPTIONAL {{ ?bien :numeroAffiliationCNAM ?cnam }}
  OPTIONAL {{ ?bien :valeurVenale ?v1 }} OPTIONAL {{ ?bien :valeurDeclaree ?v2 }}
  BIND(COALESCE(CONCAT(?marque, " ", ?modele, " (", ?immat, ")"),
                CONCAT(?tl, " — ", ?adresse),
                CONCAT("Affiliation CNAM ", ?cnam), "") AS ?descr)
  BIND(COALESCE(?v1, ?v2) AS ?val)
}}
GROUP BY ?bien ?type
ORDER BY ?type ?bien"""


def requete_assures(ids):
    valeurs = " ".join(f":{i}" for i in ids)
    return f"""SELECT ?assure (SAMPLE(?n) AS ?nom) (SAMPLE(?c) AS ?cin) (SAMPLE(?m) AS ?email)
       (SAMPLE(?p) AS ?profession)
       (GROUP_CONCAT(DISTINCT ?numContrat; separator=", ") AS ?contrats)
WHERE {{
  VALUES ?compagnie {{ {valeurs} }}
  {{ ?compagnie :estAssureurDe ?assure }}
  UNION {{ ?compagnie :emet ?contrat . ?contrat :estSouscritPar ?assure }}
  UNION {{ ?contrat :estEmisPar ?compagnie ; :estSouscritPar ?assure }}
  OPTIONAL {{ ?assure :nom ?n }} OPTIONAL {{ ?assure :cin ?c }}
  OPTIONAL {{ ?assure :email ?m }} OPTIONAL {{ ?assure :profession ?p }}
  OPTIONAL {{ ?ct :estEmisPar ?compagnie ; :estSouscritPar ?assure ; :numeroContrat ?numContrat }}
}}
GROUP BY ?assure
ORDER BY ?nom ?assure"""


def signaler_doublons(lignes):
    """Ajoute une remarque quand deux individus portent le même CIN (clé OWL de Assure)."""
    par_cin = {}
    for l in lignes:
        par_cin.setdefault(l["cin"], []).append(l["assure"])
    for l in lignes:
        autres = [a for a in par_cin.get(l["cin"], []) if a != l["assure"]] if l["cin"] else []
        l["remarque"] = f"Doublon probable de {', '.join(autres)} (même CIN)" if autres else ""
    return lignes


# ---------- Enregistrement ----------
nlp.enregistrer(nlp.Intention(
    nom="biens_assure",
    libelle="Biens d'un assuré",
    exemples=["Quels sont les biens assurés de Ahmed ?", "Montre les biens de Ahmed.",
              "Liste les biens assurés appartenant à Ahmed."],
    score=score_biens,
    mots_cadre=BIENS | BIENS_FAIBLES | ASSURES,
    referentiel=acteurs,
    types_attendus=("Assure",),
    nom_type="assuré",
    construire=requete_biens,
    colonnes=[("bien", "Bien"), ("type", "Type"), ("description", "Description"),
              ("valeur", "Valeur (TND)"), ("liens", "Lien avec l'assuré"), ("contrats", "Contrat(s)")],
))

nlp.enregistrer(nlp.Intention(
    nom="assures_compagnie",
    libelle="Assurés d'une compagnie",
    exemples=["Quels sont les assurés de AssurTunis ?", "Liste les clients assurés par MedAssur.",
              "Qui est assuré auprès de AssurTunis ?"],
    score=score_assures,
    mots_cadre=ASSURES | COMPAGNIES | AUPRES,
    referentiel=acteurs,
    types_attendus=("CompagnieAssurance",),
    nom_type="compagnie",
    construire=requete_assures,
    colonnes=[("assure", "Assuré"), ("nom", "Nom"), ("cin", "CIN"), ("email", "Email"),
              ("profession", "Profession"), ("contrats", "Contrat(s)"), ("remarque", "Remarque")],
    formater=signaler_doublons,
))
