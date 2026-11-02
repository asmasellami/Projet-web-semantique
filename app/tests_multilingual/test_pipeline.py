from unittest.mock import patch
from app.tests_membre3.base import FusekiIsole
from app.multilingual.engine import answer
from app.multilingual.queries import build

class MultilingualPipelineTests(FusekiIsole):
    def ask_intent(self,label,question,selected=''):
        with patch('app.multilingual.engine.predict',return_value={'label':label,'accepted':True,'score':.95,'engine':'test'}):
            return answer(question,selected)

    def test_all_ten_queries_in_three_styles(self):
        cases=[
          ('biens_assure',['Les biens de Ahmed','Assets of Ahmed','warini les biens mta3 Ahmed']),
          ('assures_compagnie',['Clients de MedAssur','Customers of MedAssur','chkoun assure 3and MedAssur']),
          ('contrats_assure',['Contrats de Ahmed','Policies of Ahmed','warini les contrats mta3 Ahmed']),
          ('sinistres_filtres',['Sinistres à Tunis','Claims in Tunis','sinistres fi Tunis']),
          ('garanties_contrat',['Garanties de AUTO-2026-001','Coverage of AUTO-2026-001','garanties mta3 AUTO-2026-001']),
          ('clauses_contrat',['Clauses de AUTO-2026-001','Terms of AUTO-2026-001','clauses mta3 AUTO-2026-001']),
          ('dommages_sinistre',['Dommages de S001','Damage for S001','degats mta3 S001']),
          ('expertises_sinistre',['Expertises de S001','Assessments of S001','expertises mta3 S001']),
          ('indemnisation_sinistre',['Paiements de S001','Payments for S001','9adech tkhalles pour S001']),
          ('baremes_sinistre',['Barèmes de S001','Scales for S001','baremes mta3 S001'])]
        for label,questions in cases:
            results=[]
            for question in questions:
                with self.subTest(label=label,question=question):
                    r=self.ask_intent(label,question)
                    self.assertEqual(r.status,'ok',(question,r.message))
                    results.append({x['item'] for x in r.rows})
            self.assertEqual(results[0],results[1]);self.assertEqual(results[1],results[2])

    def test_ownership_and_coverage_differ(self):
        owned=self.ask_intent('biens_assure','What does Ahmed own?')
        covered=self.ask_intent('biens_assure','Assets covered for Ahmed')
        self.assertEqual({r['item'] for r in owned.rows},{'Vehicule_123TU4567'})
        self.assertIn('PersonneAssuree_Ahmed',{r['item'] for r in covered.rows})
        vehicle=self.ask_intent('biens_assure','Show the insured car of Ahmed')
        self.assertEqual({r['item'] for r in vehicle.rows},{'Vehicule_123TU4567'})

    def test_location_status_dates_and_zero_results(self):
        r=self.ask_intent('sinistres_filtres','Claims in Tunis under assessment')
        self.assertEqual({x['item'] for x in r.rows},{'Sinistre_S004'})
        r=self.ask_intent('sinistres_filtres','Claims in Ariana between 2026-01-01 and 2026-12-31')
        self.assertEqual(r.status,'ok');self.assertEqual(len(r.rows),3)
        r=self.ask_intent('sinistres_filtres','Claims in Atlantis')
        self.assertEqual(r.status,'empty')

    def test_invalid_and_ambiguous_dates(self):
        for text in ['Claims in October','Claims before 2026-13-01','Claims between 2026-12-01 and 2026-01-01','Claims last month','Claims in Tunis after yesterday','Claims before October 2026']:
            self.assertEqual(self.ask_intent('sinistres_filtres',text).status,'clarify')

    def test_unsupported_filters_are_not_silently_ignored(self):
        for text in ['Expired policies of Ahmed','Policies of Ahmed after 2026-01-01']:
            self.assertEqual(self.ask_intent('contrats_assure',text).status,'clarify')
        r=self.ask_intent('indemnisation_sinistre','Payments for S001 above 999999')
        self.assertEqual(r.status,'empty')
        self.assertEqual(self.ask_intent('indemnisation_sinistre','Payments for S001 above -100').status,'clarify')
        r=self.ask_intent('clauses_contrat','Exclusions in AUTO-2026-001')
        self.assertEqual({row['item'] for row in r.rows},{'Exclusion_ConduiteEtatIvresse'})
        r=self.ask_intent('garanties_contrat','Liability coverage of AUTO-2026-001')
        self.assertEqual({row['item'] for row in r.rows},{'Garantie_RC_Auto'})

    def test_ambiguous_entity_and_validated_choice(self):
        from app import sparql_service
        sparql_service.update('INSERT DATA { :Assure_Another a :Assure ; :nom "Ahmed Mansour" ; :cin "99887766" }')
        r=self.ask_intent('contrats_assure','Policies of Ahmed')
        self.assertEqual(r.status,'ambiguous');self.assertEqual(len(r.candidates),2)
        choice=next(c['ids'] for c in r.candidates if 'Assure_Ahmed' in c['ids'])
        self.assertEqual(self.ask_intent('contrats_assure','Policies of Ahmed',choice).status,'ok')
        self.assertEqual(self.ask_intent('contrats_assure','Policies of Ahmed','Assure_Unknown').status,'clarify')

    def test_new_entity_without_retraining(self):
        from app import sparql_service
        sparql_service.update('INSERT DATA { :Assure_Nour a :Assure ; :nom "Nour Test" ; :cin "88112233" . :ContractNew a :ContratAssurance ; :estSouscritPar :Assure_Nour ; :numeroContrat "NEW-1" }')
        r=self.ask_intent('contrats_assure','warini contrats mta3 Nour')
        self.assertEqual({x['item'] for x in r.rows},{'ContractNew'})

    def test_rejection_and_no_interpolated_code(self):
        for q in ['DELETE WHERE { ?s ?p ?o }','How many policies does Ahmed have?','Compare Ahmed and Salma','Does Ahmed have insurance?','Claims not compensated in Tunis']:
            self.assertIn(answer(q).status,['rejected','unsupported'])
        with self.assertRaises(ValueError):build('contrats_assure',['x } DROP ALL'],{})

    def test_missing_model_clear_message(self):
        with patch('app.multilingual.engine.predict',side_effect=FileNotFoundError):
            self.assertEqual(answer('policies of Ahmed').status,'model_unavailable')

    def test_page(self):
        page=self.client.get('/assistant/')
        self.assertContains(page,'Tunisian Darija')
        self.assertNotContains(page,'Classifieur entraîné localement')
        self.assertNotContains(page,'validation par locuteurs tunisiens encore nécessaire')
        with patch('app.multilingual.engine.predict',return_value={'label':'contrats_assure','accepted':True,'score':.95,'engine':'test'}):
            self.assertContains(self.client.get('/assistant/',{'q':'warini contrats mta3 Ahmed'}),'Contrat_Auto_2026_001')
