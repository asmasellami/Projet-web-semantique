from django.test import Client
from app.tests_membre3.base import FusekiIsole
from app.multilingual.conversation import SESSION_KEY
from app.multilingual.engine import answer

class ConversationTests(FusekiIsole):
    def state(self,client=None):return (client or self.client).session.get(SESSION_KEY,{})
    def post(self,question=None,client=None,**kwargs):
        client=client or self.client
        data={'version':self.state(client).get('version',0),**kwargs}
        if question is not None:data['q']=question
        r=client.post('/assistant/',data)
        self.assertEqual(r.status_code,302)
        page=client.get('/assistant/')
        self.assertEqual(page.status_code,200)
        return self.state(client)
    def reply(self,state):return state['history'][-1]['reply']
    def items(self,state):return {r['item'] for r in self.reply(state)['rows']}

    def test_discovery_and_dynamic_guidance(self):
        initial=self.client.get('/assistant/')
        suggestions=initial.context['suggestions']
        self.assertTrue(any(s['question']=='Show all customers' for s in suggestions))
        s=self.post('give me the name of all users')
        # The isolated test fixture adds Nadia to the three reference customers.
        self.assertEqual(len(self.reply(s)['rows']),4)
        s=self.post(action='select',item='Assure_Ahmed')
        self.assertEqual(s['focus']['kind'],'Assure')
        page=self.client.get('/assistant/')
        self.assertTrue(any('Assure_Ahmed' in x['question'] for x in page.context['suggestions']))
        s=self.post('Show his policies')
        self.assertEqual(len(self.items(s)),3)
        s=self.post('w les biens mte3ou')
        self.assertEqual(self.items(s),{'Vehicule_123TU4567','PersonneAssuree_Ahmed'})

    def test_switch_customer_does_not_reuse_old_policy(self):
        self.post('Show guarantees of AUTO-2026-001')
        s=self.post('Show policies held by Salma')
        self.assertIn('Assure_Salma',s['focus']['ids'])
        s=self.post('And its guarantees?')
        self.assertEqual(self.reply(s)['status'],'ambiguous')
        s=self.post(action='select',item=self.reply(s)['candidates'][0]['ids'])
        self.assertEqual(s['focus']['kind'],'ContratAssurance')
        self.assertEqual(self.reply(s)['status'],'ok')
        self.assertNotIn('Garantie_RC_Auto',self.items(s))

    def test_policy_followups_and_visible_selection(self):
        s=self.post('Quelles garanties inclut le contrat AUTO-2026-001 ?')
        self.assertEqual(s['focus']['kind'],'ContratAssurance')
        s=self.post('Et ses clauses ?')
        self.assertEqual(len(self.items(s)),3)
        s=self.post('And its assets?')
        self.assertEqual(self.items(s),{'Vehicule_123TU4567'})
        s=self.post('w les sinistres mte3ou')
        self.assertEqual(self.items(s),{'Sinistre_S001'})

    def test_reverse_vehicle_and_spacing(self):
        for q in ['who owns this car 123 TU 4567','À qui appartient la voiture 123TU4567 ?','karhba hedhi mta chkoun 123 TU4567']:
            s=self.post(q);self.assertEqual(self.items(s),{'Assure_Ahmed'})
        s=self.post('Which policies cover car 123 TU 4567?')
        self.assertEqual(self.items(s),{'Contrat_Auto_2025_087','Contrat_Auto_2026_001'})

    def test_direct_claim_and_customer_filter(self):
        for q in ['Show claim S001','Montre le sinistre S001','warini sinistre S001']:
            s=self.post(q);self.assertEqual(self.items(s),{'Sinistre_S001'})
        s=self.post('Show claims for Ahmed')
        self.assertEqual(self.items(s),{'Sinistre_S001'})
        s=self.post('Show claims for Salma in Tunis')
        self.assertEqual(self.reply(s)['status'],'empty')

    def test_ordinal_follows_actual_display_order(self):
        s=self.post('List all customers')
        first=self.reply(s)['rows'][0]
        s=self.post('Show the first one’s policies')
        self.assertIn(first['item'],s['focus']['ids'])
        self.assertEqual(self.reply(s)['status'],'ok')

    def test_insurer_and_policyholder(self):
        s=self.post('Which company issued AUTO-2026-001?')
        self.assertEqual(self.items(s),{'AssurTunis'})
        s=self.post(action='select',item='AssurTunis')
        s=self.post('And its policies?')
        self.assertEqual(len(self.items(s)),4)
        s=self.post('Who holds policy AUTO-2026-001?')
        self.assertEqual(self.items(s),{'Assure_Ahmed'})

    def test_ambiguous_insurance_and_help(self):
        s=self.post('give me the names of the insurances')
        self.assertEqual(self.reply(s)['status'],'clarify')
        self.assertIn('compagnies',self.reply(s)['message'])
        for q in ['What can I ask you?','Quelles questions puis-je poser ?','chnowa najem nes2lek']:
            s=self.post(q);self.assertEqual(self.reply(s)['status'],'help')

    def test_unknown_entity_never_inherits_customer(self):
        self.post('Show policies held by Ahmed')
        s=self.post('Show policies held by UnknownPerson')
        self.assertEqual(self.reply(s)['status'],'clarify')
        self.assertIn('Assure_Ahmed',s['focus']['ids'])
        self.assertFalse(self.reply(s)['rows'])

    def test_two_sessions_reset_and_get_are_isolated(self):
        self.post('Show policies held by Ahmed')
        other=Client();s=self.post('And his assets?',client=other)
        self.assertNotEqual(self.reply(s)['status'],'ok')
        s=self.post(action='reset')
        self.assertFalse(s['history']);self.assertIsNone(s['focus'])
        self.client.get('/assistant/',{'q':'Show policies held by Ahmed'})
        self.assertFalse(self.state()['history'])
        self.assertIsNone(self.state()['focus'])

    def test_tampered_and_stale_buttons(self):
        s=self.post('Show all customers');version=s['version']
        original=self.state()
        self.post(action='select',item='Contrat_Auto_2026_001')
        self.assertEqual(self.state(),original)
        self.post(action='select',item='Assure_Ahmed')
        r=self.client.post('/assistant/',{'version':version,'q':'Show all policies'})
        self.assertEqual(r.status_code,302)
        self.assertEqual(self.state()['focus']['kind'],'Assure')

    def test_deleted_focus_is_not_reused(self):
        from app import sparql_service
        self.post('Show policies held by Salma')
        sparql_service.update('DELETE WHERE { :Assure_Salma ?p ?o }')
        s=self.post('And her policies?')
        self.assertIsNone(s['focus'])
        self.assertEqual(self.reply(s)['status'],'clarify')

    def test_csrf_and_history_bound(self):
        client=Client(enforce_csrf_checks=True)
        self.assertEqual(client.post('/assistant/',{'q':'Show customers'}).status_code,403)
        for _ in range(14):s=self.post('hello')
        self.assertEqual(len(s['history']),12)

    def test_suggestions_follow_returned_records(self):
        self.post('Show all customers')
        page=self.client.get('/assistant/')
        self.assertTrue(any(s.get('item')=='Assure_Ahmed' for s in page.context['suggestions']))
        self.post(action='select',item='Assure_Ahmed')
        self.post('Show his policies')
        page=self.client.get('/assistant/')
        self.assertTrue(any(s.get('item')=='Contrat_Auto_2026_001' for s in page.context['suggestions']))
        self.post(action='select',item='Contrat_Auto_2026_001')
        page=self.client.get('/assistant/')
        self.assertTrue(any('guarantees' in s.get('question','') for s in page.context['suggestions']))
        self.assertFalse(any('Assure_Salma' in s.get('question','') for s in page.context['suggestions']))

    def test_natural_followups_from_exploration(self):
        self.post('Show policies held by Ahmed')
        s=self.post('Et ses propriétés ?')
        self.assertEqual(self.items(s),{'Vehicule_123TU4567','PersonneAssuree_Ahmed'})
        self.post('Show guarantees of AUTO-2026-001')
        s=self.post('w chkoun souscrit fih')
        self.assertEqual(self.items(s),{'Assure_Ahmed'})
        s=self.post('And its claims?')
        self.assertEqual(self.items(s),{'Sinistre_S001'})
        self.post(action='select',item='Sinistre_S001')
        s=self.post('How much was paid for this claim?')
        self.assertEqual(self.items(s),{'Indemnisation_I001'})

    def test_unknown_name_with_pronoun_does_not_borrow_focus(self):
        self.post('Show policies held by Ahmed')
        s=self.post('Show his policies for UnknownPerson')
        self.assertEqual(self.reply(s)['status'],'clarify')
        self.assertFalse(self.reply(s)['rows'])

    def test_typed_selection_and_unknown_name(self):
        s=self.post('select Ahmed');self.assertEqual(s['focus']['kind'],'Assure')
        s=self.post('Show his policies');self.assertEqual(len(self.items(s)),3)
        s=self.post('choisis Salma');self.assertEqual(s['focus']['ids'],['Assure_Salma'])
        self.assertEqual(s['last_question'],'')
        s=self.post('select UnknownPerson');self.assertEqual(self.reply(s)['status'],'clarify')
        self.assertEqual(s['focus']['ids'],['Assure_Salma'])

    def test_homonymous_bare_selection(self):
        from app import sparql_service
        sparql_service.update('INSERT DATA { :Assure_OtherAhmed a :Assure ; :nom "Ahmed Mansour" ; :cin "99114455" }')
        s=self.post('Ahmed');self.assertEqual(self.reply(s)['status'],'ambiguous')
        choice=next(c['ids'] for c in self.reply(s)['candidates'] if 'Assure_OtherAhmed' in c['ids'])
        s=self.post(action='select',item=choice)
        self.assertEqual(s['focus']['ids'],['Assure_OtherAhmed'])
