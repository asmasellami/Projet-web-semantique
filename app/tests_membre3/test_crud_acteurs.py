"""CRUD Acteur / page Assurés : formulaires, validation OWL, relations RDF, redirections."""
from .base import FusekiIsole

ASSURE = {"type": "Assure", "nom": "Karim Zouari", "cin": "12345678", "email": "karim@example.tn",
          "telephone": "+216 20 111 222", "profession": "Avocat", "anneesPermis": "10",
          "coefficientBonusMalus": "1.1", "dateNaissance": "1990-05-17"}


class ActeurCrudTests(FusekiIsole):
    def creer(self, **champs):
        return self.client.post("/acteurs/nouveau/", {**ASSURE, **champs})

    def test_creation_assure(self):
        r = self.creer()
        self.assertRedirects(r, "/acteurs/", fetch_redirect_response=False)
        # Identifiant préfixé par le sous-type, classes explicites (HermiT ne tourne pas dans Fuseki)
        self.assertTrue(self.existe(":Assure_Karim_Zouari a :Acteur, :Assure"))
        self.assertTrue(self.existe(':Assure_Karim_Zouari :cin "12345678" ; :nom "Karim Zouari" ; :identifiant "12345678"'))
        self.assertTrue(self.existe(':Assure_Karim_Zouari :coefficientBonusMalus 1.1'))
        self.assertTrue(self.existe(':Assure_Karim_Zouari :dateEvenement ?d'))

    def test_creation_autres_sous_types(self):
        self.client.post("/acteurs/nouveau/", {"type": "Expert", "nom": "Hela Ben Amor", "specialite": "Incendie",
                                               "numeroAgrement": "EXP-1", "collaboreAvec": ["STAR"]})
        self.assertTrue(self.existe(":Expert_Hela_Ben_Amor a :Acteur, :Expert ; :collaboreAvec :STAR"))
        self.client.post("/acteurs/nouveau/", {"type": "CompagnieAssurance", "nom": "Lloyd Test", "capitalSocial": "1000000",
                                               "estReassurePar": ["TunisRe"]})
        self.assertTrue(self.existe(":CompagnieAssurance_Lloyd_Test a :Acteur, :CompagnieAssurance"))
        self.client.post("/acteurs/nouveau/", {"type": "Beneficiaire", "nom": "Sana Test", "lienAvecAssure": "Fille"})
        self.assertTrue(self.existe(":Beneficiaire_Sana_Test a :Beneficiaire ; :lienAvecAssure \"Fille\""))

    def test_nom_et_cin_obligatoires(self):
        r = self.creer(nom="", cin="")
        self.assertContains(r, "« Nom » est obligatoire")
        self.assertContains(r, "« CIN » est obligatoire")

    def test_type_obligatoire(self):
        self.assertContains(self.creer(type=""), "Choisissez un type")

    def test_facettes_owl(self):
        r = self.creer(coefficientBonusMalus="4")
        self.assertContains(r, "inférieur ou égal à 3.5")
        r = self.creer(coefficientBonusMalus="0.2")
        self.assertContains(r, "supérieur ou égal à 0.5")
        self.assertContains(self.creer(anneesPermis="-1"), "supérieur ou égal à 0")
        self.assertContains(self.creer(anneesPermis="abc"), "entier")
        self.assertFalse(self.existe(":Assure_Karim_Zouari ?p ?o"))

    def test_formats(self):
        self.assertContains(self.creer(email="pas-un-email"), "Email")
        self.assertContains(self.creer(telephone="abc"), "Téléphone")
        self.assertContains(self.creer(cin="123"), "8 chiffres")
        self.assertContains(self.creer(dateNaissance="31/12/1990"), "Date invalide")

    def test_cin_cle_owl_unique(self):
        self.assertContains(self.creer(cin="08123456"), "porte déjà ce CIN")

    def test_doublon_historique_reste_modifiable(self):
        r = self.client.post("/acteurs/Client_CRM_4471/modifier/", {
            "type": "Assure", "nom": "Ahmed Ben Salah", "cin": "08123456", "telephone": "+216 98 000 999"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(self.existe(':Client_CRM_4471 :telephone "+216 98 000 999"'))

    def test_modifier_cin_vers_cin_existant_refuse(self):
        r = self.client.post("/acteurs/Assure_Salma/modifier/", {"type": "Assure", "nom": "Salma Trabelsi", "cin": "07456123"})
        self.assertContains(r, "porte déjà ce CIN")

    def test_creation_deux_fois_meme_nom(self):
        self.creer()
        self.assertContains(self.creer(cin="87654321"), "existe déjà")

    def test_modification(self):
        self.creer()
        r = self.client.post("/acteurs/Assure_Karim_Zouari/modifier/",
                             {**ASSURE, "profession": "Notaire", "coefficientBonusMalus": "0.9"})
        self.assertRedirects(r, "/acteurs/", fetch_redirect_response=False)
        self.assertTrue(self.existe(':Assure_Karim_Zouari :profession "Notaire"'))
        self.assertFalse(self.existe(':Assure_Karim_Zouari :profession "Avocat"'))
        self.assertTrue(self.existe(":Assure_Karim_Zouari :coefficientBonusMalus 0.9"))

    def test_relations_rdf_avec_inverses(self):
        self.creer(estProprietaireDe=["Vehicule_123TU4567"], estCoAssureAvec=["Assure_Salma"])
        self.assertTrue(self.existe(":Assure_Karim_Zouari :estProprietaireDe :Vehicule_123TU4567"))
        self.assertTrue(self.existe(":Vehicule_123TU4567 :appartientA :Assure_Karim_Zouari"))
        # Propriété symétrique : le lien existe dans les deux sens
        self.assertTrue(self.existe(":Assure_Karim_Zouari :estCoAssureAvec :Assure_Salma"))
        self.assertTrue(self.existe(":Assure_Salma :estCoAssureAvec :Assure_Karim_Zouari"))
        # Remplacement : le lien disparaît aussi côté inverse
        self.client.post("/acteurs/Assure_Karim_Zouari/modifier/", {**ASSURE})
        self.assertFalse(self.existe(":Vehicule_123TU4567 :appartientA :Assure_Karim_Zouari"))
        self.assertTrue(self.existe(":Vehicule_123TU4567 :appartientA :Assure_Ahmed"))      # lien d'un autre : intact

    def test_relation_cible_inconnue_refusee(self):
        self.assertContains(self.creer(estProprietaireDe=["Vehicule_Inexistant"]), "valeur inconnue")

    def test_suppression_retire_les_references(self):
        r = self.client.post("/acteurs/Assure_Salma/supprimer/")
        self.assertRedirects(r, "/acteurs/", fetch_redirect_response=False)
        self.assertFalse(self.existe(":Assure_Salma ?p ?o"))
        self.assertFalse(self.existe("?s ?p :Assure_Salma"))
        self.assertTrue(self.existe(":Logement_Ariana :adresse ?a"))        # le bien lui-même reste

    def test_suppression_exige_post(self):
        self.assertEqual(self.client.get("/acteurs/Assure_Salma/supprimer/").status_code, 405)

    def test_identifiants_invalides(self):
        self.assertEqual(self.client.get("/acteurs/Inexistant/modifier/").status_code, 404)
        self.assertEqual(self.client.get("/acteurs/a%20b;x/modifier/").status_code, 404)
        self.assertEqual(self.client.post("/acteurs/a%20b;x/supprimer/").status_code, 404)

    def test_liste_recherche_filtres(self):
        r = self.client.get("/acteurs/", {"q": "salma"})
        self.assertContains(r, "Salma Trabelsi")
        self.assertNotContains(r, "Youssef Gharbi")
        r = self.client.get("/acteurs/", {"type": "Expert"})
        self.assertContains(r, "Karim Jlassi")
        self.assertNotContains(r, "Salma Trabelsi")
        r = self.client.get("/acteurs/", {"min": "50000000"})
        self.assertContains(r, "Tunis")
        self.assertEqual(self.client.get("/acteurs/", {"min": "abc"}).status_code, 200)

    def test_recherche_guillemets_et_injection(self):
        for q in ('" } DROP ALL', "\\", "'; DELETE"):
            self.assertEqual(self.client.get("/acteurs/", {"q": q}).status_code, 200)
        self.assertTrue(self.existe(":Assure_Salma :nom ?n"))

    def test_preselection_du_type(self):
        r = self.client.get("/acteurs/nouveau/", {"type": "Assure"})
        self.assertContains(r, '<option value="Assure" selected>')


class RedirectionNextTests(FusekiIsole):
    def test_retour_vers_assures(self):
        r = self.client.post("/acteurs/nouveau/?next=/assures/", {**ASSURE})
        self.assertRedirects(r, "/assures/", fetch_redirect_response=False)
        r = self.client.post("/acteurs/Assure_Karim_Zouari/supprimer/", {"next": "/assures/"})
        self.assertRedirects(r, "/assures/", fetch_redirect_response=False)

    def test_next_externe_ignore(self):
        for n, cible in enumerate(("https://evil.example/", "//evil.example/", "javascript:alert(1)")):
            r = self.client.post(f"/acteurs/nouveau/?next={cible}", {**ASSURE, "cin": f"2233445{n}", "nom": f"Externe {n}"})
            self.assertRedirects(r, "/acteurs/", fetch_redirect_response=False)


class PageAssuresTests(FusekiIsole):
    def test_liste(self):
        r = self.client.get("/assures/")
        self.assertEqual(r.status_code, 200)
        for nom in ("Ahmed Ben Salah", "Salma Trabelsi", "Youssef Gharbi", "Nadia Ferchichi"):
            self.assertContains(r, nom)
        self.assertNotContains(r, "Karim Jlassi")                  # un expert n'est pas un assuré
        self.assertNotContains(r, "Mariem")

    def test_doublon_cin_signale(self):
        r = self.client.get("/assures/")
        self.assertContains(r, "Doublon de")
        self.assertEqual(r.context["stats"]["doublons"], 2)

    def test_compteurs(self):
        assures = {a["id"]: a for a in self.client.get("/assures/").context["assures"]}
        self.assertEqual(assures["Assure_Ahmed"]["nb_contrats"], 3)
        self.assertEqual(assures["Assure_Ahmed"]["nb_biens"], 1)
        self.assertEqual(assures["Assure_Ahmed"]["compagnies"], ["AssurTunis"])
        self.assertEqual(assures["Assure_Youssef"]["compagnies"], ["MedAssur"])
        self.assertEqual(assures["Assure_Nadia"]["compagnies"], ["STAR"])

    def test_filtres(self):
        def ids(**f):
            return {a["id"] for a in self.client.get("/assures/", f).context["assures"]}
        self.assertEqual(ids(q="trabelsi"), {"Assure_Salma"})
        self.assertEqual(ids(q="08123456"), {"Assure_Ahmed", "Client_CRM_4471"})
        self.assertEqual(ids(compagnie="MedAssur"), {"Assure_Youssef"})
        self.assertEqual(ids(compagnie="STAR"), {"Assure_Nadia"})
        self.assertEqual(ids(bonus_min="1"), {"Assure_Youssef"})
        self.assertEqual(ids(bonus_max="0.9"), {"Assure_Ahmed", "Client_CRM_4471"})

    def test_filtres_invalides(self):
        self.assertEqual(self.client.get("/assures/", {"bonus_min": "abc"}).status_code, 200)
        self.assertEqual(self.client.get("/assures/", {"compagnie": "x}y"}).status_code, 200)

    def test_nouvel_assure_apparait(self):
        self.client.post("/acteurs/nouveau/?next=/assures/", {**ASSURE})
        self.assertContains(self.client.get("/assures/"), "Karim Zouari")
