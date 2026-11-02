"""Read-only UX exploration audit. These cases are NOT added to training.

Visits the Django assistant route using its test client, including consecutive turns.
Expected result sets come from independent, fixed SPARQL queries on the same graph.
"""
import json
import os
import sys
from pathlib import Path
from urllib.error import URLError
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','assurance_project.settings')
import django
django.setup()
from django.test import Client, override_settings
from django.test.utils import setup_test_environment
from app import sparql_service
from app.multilingual.conversation import SESSION_KEY
from app.multilingual.engine import catalogue

# Each tuple: scenario, preceding turn, three language variants, expected graph query.
SCENARIOS=[
 ('list_customers','',['give me the name of all users','Donne-moi les noms de tous les clients','warini les noms mta3 les clients lkol'],'SELECT ?item WHERE { ?item a :Assure }'),
 ('ambiguous_insurances','',['give me the names of the insurances','Donne-moi les noms des assurances','a3tini les noms mta3 les assurances'],None),
 ('list_insurers','',['List all insurance companies','Liste toutes les compagnies d’assurance','warini les compagnies assurance lkol'],'SELECT ?item WHERE { ?item a :CompagnieAssurance }'),
 ('list_policies','',['Show all insurance contracts','Liste tous les contrats d’assurance','warini les contrats assurance lkol'],'SELECT ?item WHERE { ?item a :ContratAssurance }'),
 ('list_assets','',['Show all insured assets','Liste tous les biens assurés','warini les biens assures lkol'],'SELECT ?item WHERE { ?item a :BienAssure }'),
 ('owner_plate_123','',['who owns this car 123 TU 4567','À qui appartient la voiture 123 TU 4567 ?','karhba hedhi mta chkoun 123 TU 4567'],'SELECT DISTINCT ?item WHERE { ?v :immatriculation "123 TU 4567" ; :appartientA ?item }'),
 ('owner_plate_205','',['who owns this car 205 TU 8890','Qui possède la voiture 205 TU 8890 ?','karhba hedhi mta chkoun 205 TU 8890'],'SELECT DISTINCT ?item WHERE { ?v :immatriculation "205 TU 8890" ; :appartientA ?item }'),
 ('policy_from_vehicle','',['Which policies cover car 123 TU 4567?','Quels contrats couvrent la voiture 123 TU 4567 ?','anehom les contrats elli yghattiw karhba 123 TU 4567'],'SELECT DISTINCT ?item WHERE { ?v :immatriculation "123 TU 4567" . ?item :couvreBien ?v }'),
 ('policy_issuer','',['Which company issued AUTO-2026-001?','Quelle compagnie a émis AUTO-2026-001 ?','anehi compagnie elli 3amlet AUTO-2026-001'],'SELECT DISTINCT ?item WHERE { :Contrat_Auto_2026_001 :estEmisPar ?item }'),
 ('policy_holder','',['Who holds policy AUTO-2026-001?','Qui a souscrit le contrat AUTO-2026-001 ?','chkoun souscrit contrat AUTO-2026-001'],'SELECT DISTINCT ?item WHERE { :Contrat_Auto_2026_001 :estSouscritPar ?item }'),
 ('claim_by_id','',['Show claim S001','Montre le sinistre S001','warini sinistre S001'],'SELECT ?item WHERE { VALUES ?item { :Sinistre_S001 } ?item a :Sinistre }'),
 ('claims_of_customer','',['Show Ahmed’s claims','Liste les sinistres de Ahmed','warini les sinistres mta3 Ahmed'],'SELECT DISTINCT ?item WHERE { ?item a :Sinistre ; :concerneContrat ?c . ?c :estSouscritPar :Assure_Ahmed }'),
 ('missing_customer','',['Show my policies','Montre mes contrats','warini les contrats mte3i'],'clarify'),
 ('misspelled_name','',['Show policies of Ahmd','Montre les contrats de Ahmd','warini les contrats mta3 Ahmd'],'clarify'),
 ('explicit_customer','',['Show policies held by Ahmed','Quels sont les contrats de Ahmed ?','warini les contrats mta3 Ahmed'],'SELECT DISTINCT ?item WHERE { ?item :estSouscritPar :Assure_Ahmed }'),
 ('followup_assets','Show policies held by Ahmed',['And his assets?','Et ses biens ?','w les biens mte3ou'],'SELECT DISTINCT ?item WHERE { { :Assure_Ahmed :estProprietaireDe ?item } UNION { ?c :estSouscritPar :Assure_Ahmed ; :couvreBien ?item } }'),
 ('followup_guarantees','Which guarantees are included in policy AUTO-2026-001?',['And its clauses?','Et ses clauses ?','w les clauses mte3ou'],'SELECT DISTINCT ?item WHERE { :Contrat_Auto_2026_001 :contientClause ?item }'),
 ('followup_choice','List all insurance customers',['Show the first one’s policies','Montre les contrats du premier','warini contrats mta3 louleni'],'SELECT DISTINCT ?item WHERE { ?item :estSouscritPar :Assure_Ahmed }'),
 ('all_claims','',['List all claims','Liste tous les sinistres','warini les sinistres lkol'],'SELECT ?item WHERE { ?item a :Sinistre }'),
 ('help','',['What can I ask you?','Quelles questions puis-je poser ?','chnowa najem nes2lek'],'help'),
]

def main():
    sparql_service.FUSEKI=os.environ.get('FUSEKI_URL','http://127.0.0.1:3030/assurance')
    before=sparql_service.query('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }')[0]['n']['value']
    setup_test_environment()
    records=[]
    people={alias:sorted(g['ids'])[0] for g in catalogue('Assure') for alias in g['ids']}
    def normalized_ids(ids):return sorted({people.get(i,i) for i in ids})
    def ask(client,question):
        version=client.session.get(SESSION_KEY,{}).get('version',0)
        response=client.post('/assistant/',{'q':question,'version':version})
        assert response.status_code==302
        return client.session[SESSION_KEY]['history'][-1]['reply']
    with override_settings(ALLOWED_HOSTS=['testserver']):
        for scenario,prior,questions,expected in SCENARIOS:
            expected_ids=None
            if expected and expected.startswith('SELECT'):
                expected_ids=normalized_ids(r['item']['value'].split('#')[-1] for r in sparql_service.query(expected))
            for lang,q in zip(['en','fr','tn-Darija'],questions):
                client=Client()
                if prior:
                    ask(client,prior)
                rep=ask(client,q)
                actual=normalized_ids(r['item'] for r in rep['rows'])
                if expected_ids is not None:
                    outcome='correct_records' if rep['status'] in ['ok','empty'] and actual==expected_ids else 'wrong_records' if rep['status'] in ['ok','empty'] else 'not_answered'
                else:
                    outcome='appropriate_clarification' if rep['status']=='clarify' and (expected=='clarify' or (expected is None and 'compagnies' in rep['message'])) else 'helpful_guidance' if expected=='help' and rep['status']=='help' else 'not_answered'
                records.append(dict(scenario=scenario,language=lang,previous_turn=prior,question=q,status=rep['status'],intent=rep['intent'],message=rep['message'],expected_ids=expected_ids,actual_ids=actual,outcome=outcome))
    after=sparql_service.query('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }')[0]['n']['value']
    assert before==after
    from collections import Counter
    summary=dict(Counter(r['outcome'] for r in records))
    result=dict(description='Neutral exploration of discovery, reverse relationships and follow-up UX; not a language-accuracy benchmark; not training data.',triple_count_before=before,triple_count_after=after,summary=summary,records=records)
    out=Path(__file__).parent/'reports/exploration-audit.json'
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
    for scenario,_,_,_ in SCENARIOS:
        print(scenario,[(r['language'],r['status'],r['intent'],r['outcome']) for r in records if r['scenario']==scenario])

if __name__=='__main__':main()
