"""Routes communes et non-régression sur les modules des autres membres."""
from .base import FusekiIsole

PAGES = ["/", "/sinistres/", "/dommages/", "/contrats/", "/biens/", "/indemnisations/", "/baremes/",
         "/garanties/", "/clauses/", "/acteurs/", "/expertises/", "/assures/", "/question/"]
FORMULAIRES = ["/sinistres/nouveau/", "/dommages/nouveau/", "/contrats/nouveau/", "/biens/nouveau/",
               "/indemnisations/nouveau/", "/baremes/nouveau/", "/garanties/nouveau/", "/clauses/nouveau/",
               "/acteurs/nouveau/", "/expertises/nouveau/"]


class RoutesTests(FusekiIsole):
    def test_pages_de_liste(self):
        for url in PAGES:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_formulaires_de_creation(self):
        for url in FORMULAIRES:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_routes_du_guide_assures_et_biens(self):
        self.assertContains(self.client.get("/assures/"), "Assurés")
        self.assertContains(self.client.get("/biens/"), "Biens assurés")

    def test_menu_contient_les_liens_membre3(self):
        r = self.client.get("/")
        for lien in ('href="/assures/"', 'href="/biens/"', 'href="/acteurs/"', 'href="/question/"'):
            self.assertContains(r, lien)

    def test_page_inconnue(self):
        self.assertEqual(self.client.get("/inconnu/").status_code, 404)


class NonRegressionTests(FusekiIsole):
    def test_accueil_statistiques(self):
        r = self.client.get("/")
        self.assertGreater(r.context["totaux"]["classes"], 10)
        noms = {c["nom"] for c in r.context["classes"]}
        self.assertIn("Acteur", noms)

    def test_sinistres_inchanges(self):
        r = self.client.get("/sinistres/")
        self.assertEqual(len(r.context["sinistres"]), 5)          # 5 sinistres attendus par le guide

    def test_requete_du_guide(self):
        rows = self.ask("SELECT ?num ?statut WHERE { ?s :numeroDossier ?num ; :statutDossier ?statut }")
        self.assertEqual(len(rows), 5)

    def test_contrats_listent_toujours_biens_et_compagnie(self):
        contrats = {c["id"]: c for c in self.client.get("/contrats/").context["contrats"]}
        self.assertEqual(contrats["Contrat_Auto_2026_900"]["assureur"], "STAR")
        self.assertIn("Vehicule Nadia", contrats["Contrat_Auto_2026_900"]["biens"])

    def test_crud_generique_expertises(self):
        # Le moteur CRUD commun (modifié de façon rétro-compatible) fonctionne toujours pour un autre module.
        r = self.client.post("/expertises/nouveau/", {
            "numeroRapport": "RAP-TEST", "dateExpertise": "2026-10-01", "montantRetenu": "1200",
            "conclusion": "OK", "realiseePar": ["Expert_Karim"]})
        self.assertRedirects(r, "/expertises/", fetch_redirect_response=False)
        self.assertTrue(self.existe(":Expertise_RAP_TEST :numeroRapport \"RAP-TEST\" ; :realiseePar :Expert_Karim"))
        self.assertTrue(self.existe(":Expert_Karim :aRealise :Expertise_RAP_TEST"))
        r = self.client.post("/expertises/Expertise_RAP_TEST/modifier/", {
            "numeroRapport": "RAP-TEST", "dateExpertise": "2026-10-02", "montantRetenu": "1300"})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(self.existe(":Expert_Karim :aRealise :Expertise_RAP_TEST"))
        self.client.post("/expertises/Expertise_RAP_TEST/supprimer/")
        self.assertFalse(self.existe(":Expertise_RAP_TEST ?p ?o"))

    def test_identifiants_classe_conserves_pour_les_autres_entites(self):
        # prefixe_par_type n'est activé que pour les acteurs : les autres entités gardent leur préfixe de classe.
        self.client.post("/sinistres/nouveau/", {
            "type": "Vol", "numeroDossier": "SIN-TEST-1", "statutDossier": "Déclaré", "dateSinistre": "2026-10-01"})
        self.assertTrue(self.existe(":Sinistre_SIN_TEST_1 a :Sinistre, :Vol"))

    def test_creation_acteur_ne_change_pas_les_autres_classes(self):
        avant = len(self.ask("SELECT ?s WHERE { ?s a :Sinistre }"))
        self.client.post("/acteurs/nouveau/", {"type": "Beneficiaire", "nom": "Test Reg"})
        self.assertEqual(len(self.ask("SELECT ?s WHERE { ?s a :Sinistre }")), avant)


class FusekiArreteTests(FusekiIsole):
    """Quand Fuseki est injoignable, l'écriture affiche une erreur claire au lieu de planter."""

    def test_ecriture_sans_fuseki(self):
        from unittest import mock
        from urllib.error import URLError
        with mock.patch("app.services.crud.rdf.existe", side_effect=URLError("refusé")):
            r = self.client.post("/acteurs/nouveau/", {"type": "Beneficiaire", "nom": "Panne"})
        self.assertContains(r, "Fuseki est injoignable")
