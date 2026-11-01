"""CRUD BienAssure : formulaires, validation OWL (facettes, HasKey, énumération), relations RDF."""
from app.services import biens

from .base import FusekiIsole

VEHICULE = {"type": "Vehicule", "immatriculation": "150 TU 9999", "marque": "Fiat", "modele": "500",
            "anneeMiseEnCirculation": "2020", "puissanceFiscale": "5", "valeurVenale": "30000"}
LOGEMENT = {"type": "Logement", "adresse": "8 rue des Oliviers, Tunis", "typeLogement": "Duplex",
            "superficie": "140.5", "nombrePieces": "5", "valeurDeclaree": "450000"}
PERSONNE = {"type": "PersonneAssuree", "numeroAffiliationCNAM": "CNAM-1990-11111", "dateNaissance": "1990-01-02"}


class BienCrudTests(FusekiIsole):
    def creer(self, base, **champs):
        return self.client.post("/biens/nouveau/", {**base, **champs})

    def test_enumeration_logement_conforme_a_l_ontologie(self):
        lues = {r["v"]["value"].split("#")[-1] for r in self.ask(
            "SELECT ?v WHERE { :typeLogement rdfs:range ?r . ?r owl:oneOf ?l . "
            "?l <http://www.w3.org/1999/02/22-rdf-syntax-ns#rest>*/<http://www.w3.org/1999/02/22-rdf-syntax-ns#first> ?v }")}
        self.assertEqual(set(biens.TYPES_LOGEMENT), lues)

    def test_creation_vehicule_avec_relations(self):
        r = self.creer(VEHICULE, proprietaire=["Assure_Salma"], contrats=["Contrat_Hab_2026_014"])
        self.assertRedirects(r, "/biens/", fetch_redirect_response=False)
        self.assertTrue(self.existe(":Vehicule_150_TU_9999 a :BienAssure, :Vehicule ; :marque \"Fiat\" ; "
                                    ":immatriculation \"150 TU 9999\" ; :identifiant \"150 TU 9999\""))
        self.assertTrue(self.existe(':Vehicule_150_TU_9999 :montant "30000"^^xsd:decimal ; :valeurVenale "30000"^^xsd:decimal'))
        # Relation et son inverse (estProprietaireDe) écrites explicitement
        self.assertTrue(self.existe(":Vehicule_150_TU_9999 :appartientA :Assure_Salma"))
        self.assertTrue(self.existe(":Assure_Salma :estProprietaireDe :Vehicule_150_TU_9999"))
        self.assertTrue(self.existe(":Contrat_Hab_2026_014 :couvreBien :Vehicule_150_TU_9999"))

    def test_creation_logement_et_personne(self):
        self.assertEqual(self.creer(LOGEMENT).status_code, 302)
        self.assertTrue(self.existe(':Logement_8_rue_des_Oliviers_Tunis :typeLogement "Duplex" ; :nombrePieces 5'))
        self.assertEqual(self.creer(PERSONNE).status_code, 302)
        self.assertTrue(self.existe(":PersonneAssuree_CNAM_1990_11111 a :PersonneAssuree ; :dateEvenement ?d"))

    def test_champs_obligatoires(self):
        r = self.creer(VEHICULE, marque="", valeurVenale="")
        self.assertContains(r, "« Marque » est obligatoire")
        self.assertContains(r, "Valeur vénale")
        self.assertContains(self.creer({"type": ""}), "Choisissez un type")

    def test_facettes_owl(self):
        cas = [(VEHICULE, {"anneeMiseEnCirculation": "1940"}, "supérieur ou égal à 1950"),
               (VEHICULE, {"anneeMiseEnCirculation": "2999"}, "futur"),
               (VEHICULE, {"puissanceFiscale": "0"}, "supérieur ou égal à 1"),
               (VEHICULE, {"puissanceFiscale": "51"}, "inférieur ou égal à 50"),
               (VEHICULE, {"valeurVenale": "-5"}, "supérieur ou égal à 0"),
               (VEHICULE, {"valeurVenale": "abc"}, "nombre"),
               (LOGEMENT, {"superficie": "0"}, "strictement supérieur à 0"),
               (LOGEMENT, {"nombrePieces": "0"}, "supérieur ou égal à 1"),
               (PERSONNE, {"dateNaissance": "2999-01-01"}, "futur"),
               (PERSONNE, {"dateNaissance": "n'importe quoi"}, "Date invalide")]
        for base, champs, message in cas:
            self.assertContains(self.creer(base, **champs), message, msg_prefix=str(champs))

    def test_type_logement_hors_enumeration(self):
        self.assertContains(self.creer(LOGEMENT, typeLogement="Maison"), "Appartement, Duplex, Studio, Villa")
        self.assertFalse(self.existe(":Logement_8_rue_des_Oliviers_Tunis ?p ?o"))

    def test_cle_owl_immatriculation_unique(self):
        # « 123TU4567 » = « 123 TU 4567 » : la clé est comparée sans espaces
        for plaque in ("123 TU 4567", "123TU4567", "123  TU 4567"):
            self.assertContains(self.creer(VEHICULE, immatriculation=plaque), "porte déjà cette valeur")

    def test_meme_bien_deux_fois(self):
        self.creer(VEHICULE)
        self.assertContains(self.creer(VEHICULE), "porte déjà")

    def test_proprietaire_ou_contrat_inconnu(self):
        self.assertContains(self.creer(VEHICULE, proprietaire=["Inconnu"]), "Propriétaire inconnu")
        self.assertContains(self.creer(VEHICULE, contrats=["Inconnu"]), "Contrat inconnu")

    def test_modification_conserve_les_multi_proprietaires(self):
        r = self.client.post("/biens/Vehicule_123TU4567/modifier/", {
            "type": "Vehicule", "immatriculation": "123 TU 4567", "marque": "Kia", "modele": "Picanto GT",
            "anneeMiseEnCirculation": "2021", "puissanceFiscale": "4", "valeurVenale": "36000",
            "proprietaire": ["Assure_Ahmed", "Client_CRM_4471"], "contrats": ["Contrat_Auto_2026_001"]})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(self.existe(':Vehicule_123TU4567 :modele "Picanto GT" ; :valeurVenale "36000"^^xsd:decimal'))
        self.assertFalse(self.existe(':Vehicule_123TU4567 :modele "Picanto"'))
        self.assertTrue(self.existe(":Vehicule_123TU4567 :appartientA :Assure_Ahmed, :Client_CRM_4471"))
        self.assertTrue(self.existe(":Assure_Ahmed :estProprietaireDe :Vehicule_123TU4567"))
        self.assertTrue(self.existe(":Client_CRM_4471 :estProprietaireDe :Vehicule_123TU4567"))
        # Un seul contrat conservé : l'autre lien couvreBien est retiré
        self.assertFalse(self.existe(":Contrat_Auto_2025_087 :couvreBien :Vehicule_123TU4567"))
        self.assertTrue(self.existe(":Contrat_Auto_2026_001 :couvreBien :Vehicule_123TU4567"))

    def test_changement_de_proprietaire_retire_l_inverse(self):
        self.client.post("/biens/Vehicule_Nadia/modifier/", {
            **VEHICULE, "immatriculation": "300 TU 1234", "proprietaire": ["Assure_Salma"]})
        self.assertFalse(self.existe(":Assure_Nadia :estProprietaireDe :Vehicule_Nadia"))
        self.assertFalse(self.existe(":Vehicule_Nadia :appartientA :Assure_Nadia"))
        self.assertTrue(self.existe(":Assure_Salma :estProprietaireDe :Vehicule_Nadia"))

    def test_le_type_ne_change_pas_en_edition(self):
        self.client.post("/biens/Vehicule_Nadia/modifier/", {**LOGEMENT})
        self.assertTrue(self.existe(":Vehicule_Nadia a :Vehicule"))
        self.assertFalse(self.existe(":Vehicule_Nadia a :Logement"))

    def test_modifier_immatriculation_vers_une_existante_refuse(self):
        r = self.client.post("/biens/Vehicule_Nadia/modifier/", {**VEHICULE, "immatriculation": "205 TU 8890"})
        self.assertContains(r, "porte déjà")

    def test_garder_sa_propre_immatriculation(self):
        r = self.client.post("/biens/Vehicule_Nadia/modifier/", {**VEHICULE, "immatriculation": "300TU1234"})
        self.assertEqual(r.status_code, 302)

    def test_suppression(self):
        r = self.client.post("/biens/Vehicule_Nadia/supprimer/")
        self.assertRedirects(r, "/biens/", fetch_redirect_response=False)
        self.assertFalse(self.existe(":Vehicule_Nadia ?p ?o"))
        self.assertFalse(self.existe("?s ?p :Vehicule_Nadia"))
        self.assertTrue(self.existe(":Assure_Nadia :nom ?n"))
        self.assertTrue(self.existe(":Contrat_Auto_2026_900 :numeroContrat ?n"))

    def test_routes_et_methodes(self):
        self.assertEqual(self.client.get("/biens/Vehicule_Nadia/supprimer/").status_code, 405)
        self.assertEqual(self.client.get("/biens/Inexistant/modifier/").status_code, 404)
        self.assertEqual(self.client.get("/biens/x;y/modifier/").status_code, 404)
        self.assertContains(self.client.get("/biens/Vehicule_Nadia/modifier/"), "300 TU 1234")

    def test_formulaire_vierge(self):
        r = self.client.get("/biens/nouveau/")
        self.assertContains(r, "Duplex")
        self.assertNotContains(r, "Maison")
        self.assertContains(r, "Contrat(s) couvrant ce bien")
        self.assertContains(self.client.get("/biens/nouveau/?type=Logement"), '<option value="Logement" selected>')


class BienListeTests(FusekiIsole):
    def ids(self, **f):
        return {b["id"] for b in self.client.get("/biens/", f).context["biens"]}

    def test_liste_complete(self):
        self.assertEqual(self.ids(), {"Vehicule_123TU4567", "Vehicule_205TU8890", "Vehicule_Nadia",
                                      "Logement_Ariana", "PersonneAssuree_Ahmed"})

    def test_filtres(self):
        self.assertEqual(self.ids(type="Logement"), {"Logement_Ariana"})
        self.assertEqual(self.ids(proprietaire="Assure_Salma"), {"Logement_Ariana"})
        self.assertEqual(self.ids(valeur_min="40000", valeur_max="300000"), {"Vehicule_205TU8890", "Logement_Ariana"})

    def test_recherche(self):
        self.assertEqual(self.ids(q="picanto"), {"Vehicule_123TU4567"})
        self.assertEqual(self.ids(q="ariana"), {"Logement_Ariana"})
        self.assertEqual(self.ids(q="CNAM-1988"), {"PersonneAssuree_Ahmed"})
        self.assertEqual(self.ids(q="205 tu"), {"Vehicule_205TU8890"})

    def test_contrats_et_proprietaires_affiches(self):
        b = next(b for b in self.client.get("/biens/").context["biens"] if b["id"] == "Vehicule_123TU4567")
        self.assertEqual(set(b["proprietaires"]), {"Assure Ahmed", "Client CRM 4471"})
        self.assertEqual(set(b["contrats"]), {"Contrat Auto 2025 087", "Contrat Auto 2026 001"})

    def test_entrees_invalides(self):
        for f in ({"valeur_min": "abc"}, {"proprietaire": "a b;c"}, {"q": '" } DROP ALL'}, {"type": "Inconnu"}):
            self.assertEqual(self.client.get("/biens/", f).status_code, 200, f)
        self.assertTrue(self.existe(":Assure_Salma :nom ?n"))
