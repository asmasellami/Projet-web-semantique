"""Tests d'intégration du NLP : question -> SPARQL -> Fuseki (dataset de test isolé) -> résultats."""
from urllib.parse import quote

from app import nlp

from .base import FusekiIsole, compter_triplets, DATASET_TEST


def valeurs(rep, colonne):
    cles = [v for v, lib in rep.intention.colonnes]
    i = rep.colonnes.index(colonne)
    return [l[cles[i]] for l in rep.lignes]


class IntentionBiensTests(FusekiIsole):
    def test_questions_du_sujet(self):
        for q in ("Quels sont les biens assurés de Ahmed ?", "Montre les biens de Ahmed.",
                  "Liste les biens assurés appartenant à Ahmed.", "quels sont les biens assures de AHMED"):
            r = nlp.repondre(q)
            self.assertEqual(r.statut, "ok", (q, r.message))
            self.assertEqual(r.intention.nom, "biens_assure")
            self.assertEqual({e.id for e in r.entites}, {"Assure_Ahmed", "Client_CRM_4471"})
            self.assertEqual(sorted(valeurs(r, "Bien")), ["PersonneAssuree Ahmed", "Vehicule 123TU4567"])

    def test_details_du_vehicule(self):
        r = nlp.repondre("Quels sont les biens de Ahmed ?")
        vehicule = next(l for l in r.lignes if l["bien"].startswith("Vehicule"))
        self.assertEqual(vehicule["description"], "Kia Picanto (123 TU 4567)")
        self.assertEqual(vehicule["valeur"], "38000.0")
        self.assertIn("AUTO-2026-001", vehicule["contrats"])
        self.assertIn("propriétaire", vehicule["liens"])

    def test_bien_couvert_sans_etre_possede(self):
        # La personne assurée (santé) n'a pas de propriétaire : elle est trouvée via le contrat souscrit.
        r = nlp.repondre("biens de Ahmed")
        personne = next(l for l in r.lignes if l["bien"].startswith("PersonneAssuree"))
        self.assertEqual(personne["contrats"], "SANTE-2026-031")

    def test_autres_assures(self):
        self.assertEqual(valeurs(nlp.repondre("biens de Salma"), "Bien"), ["Logement Ariana"])
        self.assertEqual(valeurs(nlp.repondre("biens de Youssef Gharbi"), "Bien"), ["Vehicule 205TU8890"])
        self.assertEqual(valeurs(nlp.repondre("biens de Nadia"), "Bien"), ["Vehicule Nadia"])

    def test_assure_sans_bien(self):
        from app import sparql_service
        sparql_service.update('INSERT DATA { :Assure_Vide a :Acteur, :Assure ; :nom "Samir Vide" ; :cin "99998888" }')
        r = nlp.repondre("Quels sont les biens de Samir ?")
        self.assertEqual(r.statut, "ok")
        self.assertEqual(r.lignes, [])
        self.assertIn("Aucun résultat", r.message)

    def test_donnees_creees_par_l_application_sans_inference(self):
        # Fuseki ne lance pas HermiT : la requête passe par les contrats, pas seulement par les propriétés inférées.
        from app import sparql_service
        sparql_service.update("""INSERT DATA {
            :Assure_Nadia :souscrit :Contrat_Nouveau . :Contrat_Nouveau :estSouscritPar :Assure_Nadia ;
                :couvreBien :Logement_Nouveau . :Logement_Nouveau a :BienAssure, :Logement ; :adresse "5 rue X" }""")
        self.assertIn("Logement Nouveau", valeurs(nlp.repondre("biens de Nadia"), "Bien"))


class IntentionAssuresTests(FusekiIsole):
    def test_questions_du_sujet_avec_star(self):
        for q in ("Quels sont les assurés de STAR ?", "Liste les clients assurés par STAR.",
                  "Qui est assuré auprès de STAR ?"):
            r = nlp.repondre(q)
            self.assertEqual(r.statut, "ok", (q, r.message))
            self.assertEqual(r.intention.nom, "assures_compagnie")
            self.assertEqual([e.id for e in r.entites], ["STAR"])
            self.assertEqual(valeurs(r, "Nom"), ["Nadia Ferchichi"])
            self.assertEqual(valeurs(r, "Contrat(s)"), ["AUTO-2026-900"])

    def test_assurtunis_inclut_les_doublons_signales(self):
        r = nlp.repondre("Quels sont les assurés de AssurTunis ?")
        self.assertEqual(r.statut, "ok")
        self.assertEqual(valeurs(r, "Nom").count("Ahmed Ben Salah"), 2)
        self.assertIn("Salma Trabelsi", valeurs(r, "Nom"))
        remarques = [l["remarque"] for l in r.lignes if l["nom"] == "Ahmed Ben Salah"]
        self.assertTrue(all("même CIN" in x for x in remarques))
        self.assertNotIn("Youssef Gharbi", valeurs(r, "Nom"))      # assuré de MedAssur

    def test_medassur(self):
        r = nlp.repondre("Liste les clients assurés par MedAssur.")
        self.assertEqual(valeurs(r, "Nom"), ["Youssef Gharbi"])

    def test_nom_de_societe_complet_ou_partiel(self):
        for q in ("assurés de STAR Assurances", "assurés de star", "assures de Star Assurance"):
            self.assertEqual(valeurs(nlp.repondre(q), "Nom"), ["Nadia Ferchichi"], q)

    def test_compagnie_inconnue(self):
        r = nlp.repondre("Quels sont les assurés de Zurich ?")
        self.assertEqual(r.statut, "entite_inconnue")
        self.assertIn("STAR Assurances", r.resolution.suggestions)

    def test_compagnie_sans_assure(self):
        r = nlp.repondre("Quels sont les assurés de TunisRe ?")
        self.assertEqual(r.statut, "ok")
        self.assertEqual(r.lignes, [])


class SecuriteIntegrationTests(FusekiIsole):
    def test_injections_n_alterent_pas_les_donnees(self):
        avant = compter_triplets(DATASET_TEST)
        for q in ('biens de Ahmed" } ; DROP ALL ; { "', "assurés de STAR ; DELETE WHERE { ?s ?p ?o }",
                  "biens de Ahmed UNION SELECT", "biens de <http://evil.example/x>", "biens de 'Ahmed' OR 1=1",
                  "assurés de STAR DROP ALL", "biens de Ahmed\\u0022"):
            r = nlp.repondre(q)
            self.assertNotIn(r.statut, ("erreur", "erreur_fuseki"), q)
            self.assertNotIn("DROP", r.requete)
        self.assertEqual(compter_triplets(DATASET_TEST), avant)

    def test_guillemets_dans_le_nom_sont_neutralises(self):
        r = nlp.repondre('biens de "Ahmed"')
        self.assertEqual(r.statut, "ok")

    def test_entite_imposee_inconnue(self):
        r = nlp.repondre("biens de Ahmed", entite="Assure_Inexistant")
        self.assertEqual(r.statut, "entite_inconnue")
        r = nlp.repondre("biens de Ahmed", entite="X} DROP ALL")
        self.assertEqual(r.statut, "entite_inconnue")


class PageQuestionTests(FusekiIsole):
    def get(self, q, **extra):
        return self.client.get("/question/", {"q": q, **extra})

    def test_page_vide(self):
        r = self.client.get("/question/")
        self.assertContains(r, "Poser une question")
        self.assertNotContains(r, "Requête SPARQL générée")

    def test_affiche_question_intention_parametres_requete_resultats(self):
        r = self.get("Quels sont les biens assurés de Ahmed ?")
        for attendu in ("Quels sont les biens assurés de Ahmed ?", "Biens d&#x27;un assuré", "biens_assure",
                        "Assure_Ahmed", "Client_CRM_4471", "SELECT ?bien", "VALUES ?assure",
                        "Kia Picanto (123 TU 4567)"):
            self.assertContains(r, attendu)

    def test_page_assures_compagnie(self):
        r = self.get("Quels sont les assurés de STAR ?")
        self.assertContains(r, "Nadia Ferchichi")
        self.assertContains(r, "assures_compagnie")

    def test_ambiguite_propose_des_choix(self):
        from app import sparql_service
        sparql_service.update('INSERT DATA { :Assure_AM a :Acteur, :Assure ; :nom "Ahmed Mansour" ; :cin "55667788" }')
        r = self.get("Quels sont les biens de Ahmed ?")
        self.assertContains(r, "Précisez votre choix")
        self.assertContains(r, "entite=Assure_AM")
        r = self.get("Quels sont les biens de Ahmed ?", entite="Assure_AM")
        self.assertContains(r, "Aucun résultat")

    def test_erreurs_affichees(self):
        self.assertContains(self.get("Bonjour"), "Intention non reconnue")
        self.assertContains(self.get("biens de { x }"), "caractères réservés")
        self.assertContains(self.get("Quels sont les assurés de Zurich ?"), "Valeurs connues")
        self.assertEqual(self.get("x" * 400).status_code, 200)

    def test_html_echappe(self):
        r = self.get("biens de <script>alert(1)</script>")
        self.assertNotContains(r, "<script>alert(1)</script>")
        r = self.get("biens de Zorro&amp;")
        self.assertEqual(r.status_code, 200)


class ScenarioDemonstrationTests(FusekiIsole):
    """Scénario de soutenance : on crée une compagnie et un contrat par l'interface, puis on interroge en français."""

    def test_de_la_creation_a_la_question(self):
        self.client.post("/acteurs/nouveau/", {"type": "CompagnieAssurance", "nom": "COMAR", "capitalSocial": "5000000"})
        r = self.client.post("/contrats/nouveau/", {
            "type": "ContratHabitation", "numero": "HAB-DEMO-1", "statut": "Actif", "prime": "500",
            "date_debut": "2026-01-01", "date_fin": "2026-12-31", "mode": "Annuel",
            "estSouscritPar": ["Assure_Salma"], "estEmisPar": ["CompagnieAssurance_COMAR"],
            "couvreBien": ["Logement_Ariana"]})
        self.assertEqual(r.status_code, 302, "création du contrat")
        # Aucun raisonnement HermiT n'a tourné : estAssureurDe n'existe pas pour COMAR, la question marche quand même.
        self.assertFalse(self.existe(":CompagnieAssurance_COMAR :estAssureurDe ?x"))
        rep = nlp.repondre("Quels sont les assurés de COMAR ?")
        self.assertEqual(rep.statut, "ok", rep.message)
        self.assertEqual(valeurs(rep, "Nom"), ["Salma Trabelsi"])
        self.assertEqual(valeurs(rep, "Contrat(s)"), ["HAB-DEMO-1"])

    def test_nouvel_assure_puis_ses_biens(self):
        self.client.post("/acteurs/nouveau/", {"type": "Assure", "nom": "Rim Gharsallah", "cin": "13572468"})
        self.client.post("/biens/nouveau/", {
            "type": "Vehicule", "immatriculation": "222 TU 2222", "marque": "Dacia", "modele": "Sandero",
            "valeurVenale": "22000", "proprietaire": ["Assure_Rim_Gharsallah"]})
        rep = nlp.repondre("Montre les biens de Rim.")
        self.assertEqual(rep.statut, "ok", rep.message)
        self.assertEqual(valeurs(rep, "Description"), ["Dacia Sandero (222 TU 2222)"])
