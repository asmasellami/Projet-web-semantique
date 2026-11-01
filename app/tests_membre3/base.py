"""Socle des tests du membre 3 : Fuseki isolé.

Toutes les écritures des tests vont dans le dataset `assurance_member3_test`, jamais dans `assurance`.
Ce dataset de test est EN MÉMOIRE (dbType=mem) : il est créé automatiquement s'il n'existe pas, et
n'a aucun fichier TDB2 à corrompre (un dataset TDB2 vidé et rechargé en boucle a fini par bloquer Jena 5.6.0).
Avant chaque test, ce dataset de test est vidé puis rechargé avec l'ontologie officielle :
1. le fichier indiqué par la variable ASSURANCE_OWL ;
2. sinon docs/references/assurance_inferee.owl (références locales, non versionnées) ;
3. sinon une copie en lecture seule des triplets du dataset `assurance`.
Un jeu d'essai minimal (compagnie STAR, assurée Nadia, véhicule) est ajouté pour tester le cas « STAR ».
"""
import json
import os
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from django.test import TestCase

from app import sparql_service

HOTE = "http://localhost:3030"
DATASET_TEST = "assurance_member3_test"
DATASET_PRINCIPAL = "assurance"
URL_TEST = f"{HOTE}/{DATASET_TEST}"
RACINE = Path(__file__).resolve().parents[2]

JEU_ESSAI = """
INSERT DATA {
  :STAR a owl:NamedIndividual, :Acteur, :CompagnieAssurance ;
        :nom "STAR Assurances" ; :numeroAgrement "CGA-AG-099" ; :emet :Contrat_Auto_2026_900 .
  :Assure_Nadia a owl:NamedIndividual, :Acteur, :Assure ;
        :nom "Nadia Ferchichi" ; :cin "11223344" ; :email "nadia@example.tn" ; :profession "Médecin" ;
        :souscrit :Contrat_Auto_2026_900 ; :estProprietaireDe :Vehicule_Nadia .
  :Vehicule_Nadia a owl:NamedIndividual, :BienAssure, :Vehicule ;
        :immatriculation "300 TU 1234" ; :marque "Renault" ; :modele "Clio" ;
        :valeurVenale "25000.0"^^xsd:decimal ; :appartientA :Assure_Nadia .
  :Contrat_Auto_2026_900 a owl:NamedIndividual, :ContratAssurance, :ContratAuto ;
        :numeroContrat "AUTO-2026-900" ; :estEmisPar :STAR ; :estSouscritPar :Assure_Nadia ;
        :couvreBien :Vehicule_Nadia .
}
"""


def _requete(url, donnees=None, entetes=None, methode=None):
    req = Request(url, data=donnees, headers=entetes or {}, method=methode)
    with urlopen(req, timeout=20) as r:
        return r.read()


def _owl_officiel():
    chemin = Path(os.environ.get("ASSURANCE_OWL", RACINE / "docs" / "references" / "assurance_inferee.owl"))
    if chemin.is_file():
        return chemin.read_bytes(), "application/rdf+xml"
    # Repli : copie des triplets du dataset principal (lecture seule).
    return _requete(f"{HOTE}/{DATASET_PRINCIPAL}/data", entetes={"Accept": "text/turtle"}), "text/turtle"


def assurer_dataset_test():
    """Crée le dataset de test en mémoire s'il n'existe pas encore."""
    try:
        compter_triplets(DATASET_TEST)
    except URLError:
        corps = f"dbName={DATASET_TEST}&dbType=mem".encode()
        _requete(f"{HOTE}/$/datasets", corps, {"Content-Type": "application/x-www-form-urlencoded"})
        compter_triplets(DATASET_TEST)


def compter_triplets(dataset):
    q = quote("SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }")
    brut = _requete(f"{HOTE}/{dataset}/query?query={q}", entetes={"Accept": "application/sparql-results+json"})
    return int(json.loads(brut)["results"]["bindings"][0]["n"]["value"])


class FusekiIsole(TestCase):
    """Chaque test démarre sur un dataset de test propre ; le dataset `assurance` n'est jamais écrit."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            cls.triplets_principal = compter_triplets(DATASET_PRINCIPAL)
            assurer_dataset_test()
        except (URLError, OSError) as err:
            raise unittest.SkipTest(f"Fuseki ou dataset {DATASET_TEST} indisponible : {err}")
        cls._patch = mock.patch.object(sparql_service, "FUSEKI", URL_TEST)
        cls._patch.start()
        cls.owl, cls.type_owl = _owl_officiel()

    @classmethod
    def tearDownClass(cls):
        cls._patch.stop()
        # Garde-fou : le dataset principal n'a pas été modifié par les tests.
        assert compter_triplets(DATASET_PRINCIPAL) == cls.triplets_principal, "Le dataset principal a changé !"
        super().tearDownClass()

    def setUp(self):
        super().setUp()
        assert sparql_service.FUSEKI.endswith(DATASET_TEST), "Les tests ne doivent écrire que dans le dataset de test"
        _requete(f"{URL_TEST}/update", b"update=" + b"DROP+ALL",
                 {"Content-Type": "application/x-www-form-urlencoded"})
        _requete(f"{URL_TEST}/data", self.owl, {"Content-Type": self.type_owl})
        sparql_service.update(JEU_ESSAI)

    # Aides
    def ask(self, requete):
        return sparql_service.query(requete)

    def existe(self, triplet):
        return bool(self.ask(f"SELECT * WHERE {{ {triplet} }} LIMIT 1"))
