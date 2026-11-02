"""Fresh multi-turn UX checks through POST/redirect/GET, outside classifier training."""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','assurance_project.settings')
import django
django.setup()
from django.test import Client,override_settings
from django.test.utils import setup_test_environment
from app import sparql_service
from app.multilingual.conversation import SESSION_KEY

def main():
    sparql_service.FUSEKI=os.environ.get('FUSEKI_URL','http://127.0.0.1:3030/assurance')
    setup_test_environment();records=[]
    before=sparql_service.query('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }')[0]['n']['value']
    versions={
      'en':['I would like to browse customers','Show his policies','And his properties?','Whose vehicle is 205TU8890?','Which policies cover that vehicle?','Who issued it?','And its holder?','And its claims?','How much was paid for this claim?'],
      'fr':['Je voudrais voir les clients','Montre ses contrats','Et ses propriétés ?','Le propriétaire de la voiture 205 TU 8890 ?','Quels contrats couvrent cette voiture ?','Quelle compagnie a émis ce contrat ?','Et son souscripteur ?','Et ses sinistres ?','Quelle indemnisation pour ce sinistre ?'],
      'tn-Darija':['n7eb nchouf les clients','warini les contrats mte3ou','w les biens mte3ou','karhba 205 TU8890 mta chkoun','anehom contrats yghattiw karhba hedhi','anehi compagnie elli 3amlet contrat hedha','w chkoun souscrit fih','w les sinistres mte3ou','9adech tkhalles pour sinistre hedha'],
    }
    with override_settings(ALLOWED_HOSTS=['testserver']):
        for language,questions in versions.items():
            client=Client()
            def state():return client.session.get(SESSION_KEY,{})
            def send(q=None,**action):
                data={'version':state().get('version',0),**action}
                if q is not None:data['q']=q
                response=client.post('/assistant/',data);assert response.status_code==302
                page=client.get('/assistant/');assert page.status_code==200
                return state()['history'][-1]['reply'],page
            def check(step,rep,expected):
                actual={r['item'] for r in rep['rows']}
                correct=actual==set(expected) and rep['status'] in ['ok','empty']
                records.append(dict(language=language,step=step,question=rep['question'],status=rep['status'],intent=rep['intent'],expected=sorted(expected),actual=sorted(actual),correct=correct))
            rep,_=send(questions[0]);check('discover',rep,['Assure_Ahmed','Assure_Salma','Assure_Youssef'])
            rep,page=send(action='select',item='Assure_Ahmed')
            assert any('Assure_Ahmed' in s.get('question','') for s in page.context['suggestions'])
            rep,_=send(questions[1]);check('policies',rep,['Contrat_Auto_2025_087','Contrat_Auto_2026_001','Contrat_Sante_2026_031'])
            rep,_=send(questions[2]);check('assets',rep,['Vehicule_123TU4567','PersonneAssuree_Ahmed'])
            rep,_=send(questions[3]);check('reverse-owner',rep,['Assure_Youssef'])
            rep,_=send(questions[4]);check('vehicle-policies',rep,['Contrat_Auto_2026_112'])
            send(action='select',item='Contrat_Auto_2026_112')
            rep,_=send(questions[5]);check('issuer',rep,['MedAssur'])
            rep,_=send(questions[6]);check('holder',rep,['Assure_Youssef'])
            rep,_=send(questions[7]);check('policy-claims',rep,['Sinistre_S004'])
            send(action='select',item='Sinistre_S004')
            rep,_=send(questions[8]);check('empty-payment',rep,[])
            # Keep a renderable populated transcript for visual QA, not user data.
            out=Path(__file__).parent/'visual-qa';out.mkdir(exist_ok=True)
            html=client.get('/assistant/').content.decode().replace('<head>','<head><base href="http://127.0.0.1:8000/">',1)
            (out/f'{language}.html').write_text(html,encoding='utf-8')
    after=sparql_service.query('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }')[0]['n']['value'];assert before==after
    report=dict(provenance='AI-authored fresh journey wording, not native-reviewed; behavioral checks, not population accuracy.',checks=len(records),correct=sum(r['correct'] for r in records),triples_before=before,triples_after=after,records=records)
    (Path(__file__).parent/'reports/conversation-journeys.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
