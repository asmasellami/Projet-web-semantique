"""Tests unitaires du NLP : spaCy réel, mais sans Fuseki (référentiel simulé)."""
from django.test import SimpleTestCase

from app import nlp, intentions_membre3
from app.nlp import EntiteConnue

REFERENTIEL = [
    EntiteConnue("Assure_Ahmed", "Ahmed Ben Salah", {"Assure"}, "08123456"),
    EntiteConnue("Client_CRM_4471", "Ahmed Ben Salah", {"Assure"}, "08123456"),
    EntiteConnue("Assure_Salma", "Salma Trabelsi", {"Assure"}, "09876543"),
    EntiteConnue("Assure_Ahmed_Mansour", "Ahmed Mansour", {"Assure"}, "55667788"),
    EntiteConnue("Assure_Leila", "Leïla Mansour", {"Assure"}, "11112222"),
    EntiteConnue("Beneficiaire_Mariem", "Mariem Ben Salah", {"Beneficiaire"}),
    EntiteConnue("AssurTunis", "AssurTunis SA", {"CompagnieAssurance"}),
    EntiteConnue("MedAssur", "MedAssur SA", {"CompagnieAssurance"}),
    EntiteConnue("STAR", "STAR Assurances", {"CompagnieAssurance"}),
]


def rep(question, **kw):
    return nlp.repondre(question, referentiel=REFERENTIEL, executer=False, **kw)


class NettoyageTests(SimpleTestCase):
    def test_vide(self):
        for q in ("", "   ", None):
            self.assertEqual(nlp.repondre(q).statut, "vide")

    def test_trop_long(self):
        self.assertEqual(nlp.repondre("a" * 301).statut, "invalide")

    def test_caracteres_sparql_refuses(self):
        for q in ('Ahmed" } UNION { ?s ?p ?o } #', "biens de <http://x>", "assurés de STAR; DROP ALL", "a\\b"):
            self.assertEqual(nlp.repondre(q).statut, "invalide", q)

    def test_apostrophes_et_guillemets(self):
        self.assertEqual(nlp.nettoyer("biens d’Ahmed « Ben Salah »"), "biens d'Ahmed Ben Salah")

    def test_sans_accents(self):
        self.assertEqual(nlp.sans_accents("Leïla ÉLÈVE"), "leila eleve")


class IntentionTests(SimpleTestCase):
    def intention(self, q):
        return rep(q).intention.nom if rep(q).intention else None

    def test_biens_variantes(self):
        for q in ("Quels sont les biens assurés de Ahmed ?", "Montre les biens de Ahmed.",
                  "Liste les biens assurés appartenant à Ahmed.", "quels sont les biens assures de ahmed",
                  "QUELS SONT LES BIENS DE AHMED", "Biens d'Ahmed", "Donne-moi les véhicules de Salma"):
            self.assertEqual(self.intention(q), "biens_assure", q)

    def test_assures_variantes(self):
        for q in ("Quels sont les assurés de STAR ?", "Liste les clients assurés par STAR.",
                  "Qui est assuré auprès de STAR ?", "quels sont les assures de star", "Clients de AssurTunis",
                  "Qui est assuré chez MedAssur ?"):
            self.assertEqual(self.intention(q), "assures_compagnie", q)

    def test_assure_apres_biens_ne_declenche_pas_l_autre_intention(self):
        r = rep("Quels sont les biens assurés de Ahmed ?")
        scores = {s["intention"].nom: s["score"] for s in r.scores}
        self.assertEqual(scores["assures_compagnie"], 0)

    def test_hors_sujet(self):
        for q in ("Bonjour", "Quel temps fait-il demain ?", "blabla"):
            self.assertEqual(rep(q).statut, "intention_inconnue", q)


class EntiteTests(SimpleTestCase):
    def test_mentions(self):
        cas = {"Quels sont les biens assurés de Ahmed ?": "Ahmed",
               "Montre les biens de Salma Trabelsi.": "Salma Trabelsi",
               "Liste les biens assurés appartenant à Ahmed.": "Ahmed",
               "Quels sont les assurés de STAR ?": "STAR",
               "Qui est assuré auprès de AssurTunis ?": "AssurTunis",
               "Liste les clients assurés par MedAssur.": "MedAssur",
               "biens d'Ahmed Ben-Salah": "Ahmed Ben Salah"}
        for q, attendu in cas.items():
            self.assertEqual(rep(q).mention.replace("-", " "), attendu, q)

    def test_doublon_regroupe_en_une_personne(self):
        r = rep("biens d'Ahmed Ben Salah")
        self.assertEqual(r.statut, "ok")
        self.assertEqual({e.id for e in r.entites}, {"Assure_Ahmed", "Client_CRM_4471"})

    def test_homonymes_distincts_ambigus(self):
        r = rep("Quels sont les biens de Ahmed ?")
        self.assertEqual(r.statut, "ambigue")
        self.assertEqual(len(r.resolution.groupes), 2)

    def test_choix_explicite_apres_ambiguite(self):
        r = rep("Quels sont les biens de Ahmed ?", entite="Assure_Ahmed_Mansour")
        self.assertEqual(r.statut, "ok")
        self.assertIn(":Assure_Ahmed_Mansour", r.requete)
        self.assertNotIn("Client_CRM_4471", r.requete)

    def test_accents_et_casse(self):
        self.assertEqual([e.id for e in rep("biens de leila").entites], ["Assure_Leila"])
        self.assertEqual([e.id for e in rep("BIENS DE LÉÏLA").entites], ["Assure_Leila"])

    def test_faute_de_frappe(self):
        r = rep("biens de Salmaa")
        self.assertEqual([e.id for e in r.entites], ["Assure_Salma"])
        self.assertEqual(r.niveau_resolution, 1)

    def test_entite_inconnue_avec_suggestions(self):
        r = rep("Quels sont les biens de Zinedine ?")
        self.assertEqual(r.statut, "entite_inconnue")
        self.assertTrue(r.resolution.suggestions)

    def test_mauvais_type(self):
        self.assertEqual(rep("Quels sont les biens de Mariem ?").statut, "autre_type")
        self.assertEqual(rep("Quels sont les assurés de Salma ?").statut, "autre_type")
        self.assertEqual(rep("Quels sont les biens de STAR ?").statut, "autre_type")

    def test_entite_manquante(self):
        self.assertEqual(rep("Quels sont les biens ?").statut, "entite_manquante")


class SecuriteTests(SimpleTestCase):
    def test_texte_libre_jamais_dans_la_requete(self):
        r = rep("Quels sont les biens de Ahmed Mansour ?")
        self.assertEqual(r.statut, "ok")
        self.assertNotIn("Mansour", r.requete.replace("Assure_Ahmed_Mansour", ""))

    def test_injections_sans_requete_generee(self):
        attaques = ['biens de Ahmed" . } DROP ALL #', "biens de Ahmed'; DELETE WHERE {?s ?p ?o}",
                    "assurés de STAR UNION SELECT * WHERE", "biens de Ahmed\\u0022 } {",
                    "biens de ?s ?p ?o", "biens de Ahmed ) } LOAD <http://evil>"]
        for q in attaques:
            r = rep(q)
            self.assertNotIn("DROP", r.requete, q)
            self.assertNotIn("DELETE", r.requete, q)
            self.assertNotIn("LOAD", r.requete, q)
            self.assertNotIn("evil", r.requete, q)

    def test_verifier_requete_refuse_ecriture(self):
        for q in ("INSERT DATA { :a :b :c }", "SELECT * WHERE { ?s ?p ?o } ; DROP ALL",
                  "DELETE WHERE { ?s ?p ?o }", "LOAD <http://x>"):
            with self.assertRaises(ValueError):
                nlp.verifier_requete(q)
        nlp.verifier_requete(intentions_membre3.requete_biens(["Assure_Ahmed"]))
        nlp.verifier_requete(intentions_membre3.requete_assures(["AssurTunis"]))

    def test_requetes_templates(self):
        q = intentions_membre3.requete_biens(["Assure_Ahmed", "Client_CRM_4471"])
        self.assertIn("VALUES ?assure { :Assure_Ahmed :Client_CRM_4471 }", q)
        self.assertIn(":estProprietaireDe", q)
        self.assertIn(":appartientA", q)
        self.assertIn(":couvreBien", q)
        q = intentions_membre3.requete_assures(["STAR"])
        self.assertIn(":estAssureurDe", q)
        self.assertIn(":estEmisPar", q)
        self.assertIn(":estSouscritPar", q)


class SpacyTests(SimpleTestCase):
    def test_modele_francais_charge(self):
        doc = nlp.modele()("Quels sont les biens assurés de Ahmed ?")
        self.assertEqual(doc.lang_, "fr")
        self.assertTrue(doc.has_annotation("LEMMA"))

    def test_jetons_exposes(self):
        ctx = nlp.analyser_texte("Quels sont les biens assurés de Ahmed ?")
        self.assertTrue(any(j.lemme_na == "bien" for j in ctx.jetons))
