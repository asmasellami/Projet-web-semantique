"""Independent, predeclared execution challenge. Never used for model selection.

Reference ontology required. AI-authored challenge; Arabizi is not native-reviewed.
"""
import json
import os
import sys
from pathlib import Path
from time import perf_counter
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('DJANGO_SETTINGS_MODULE','assurance_project.settings')
import django
django.setup()
from app import sparql_service
from app.multilingual.engine import answer

CASES=[
 ('biens_assure',['Quels objets sont couverts par les polices de Ahmed ?', 'Please retrieve the insured property linked to Ahmed.', 'tnajem twarini chniya les biens couverts mta3 Ahmed'], {'PersonneAssuree_Ahmed','Vehicule_123TU4567'}),
 ('assures_compagnie',['Retrouve les clients assurés auprès de MedAssur.', 'Give me the people insured through MedAssur.', 'n7eb na3ref chkoun assure chez MedAssur'], {'Assure_Youssef'}),
 ('contrats_assure',['Retrouve les polices souscrites au nom de Ahmed.', 'Retrieve the insurance agreements held by Ahmed.', 'taw warini chnowa les contrats mta3 Ahmed'], {'Contrat_Auto_2025_087','Contrat_Auto_2026_001','Contrat_Sante_2026_031'}),
 ('sinistres_filtres',['Retrouve les sinistres localisés à Tunis.', 'Retrieve claims that happened in Tunis.', 'n7eb dossiers sinistres elli sarou fi Tunis'], {'Sinistre_S001','Sinistre_S004'}),
 ('garanties_contrat',['Retrouve les garanties prévues au contrat AUTO-2026-001.', 'Retrieve the guarantees attached to AUTO-2026-001.', 'taw chniya garanties elli fi AUTO-2026-001'], {'Garantie_BrisGlace_Auto','Garantie_RC_Auto'}),
 ('clauses_contrat',['Retrouve les clauses inscrites au contrat AUTO-2026-001.', 'Retrieve the terms attached to policy AUTO-2026-001.', 'taw chniya clauses elli fi AUTO-2026-001'], {'Exclusion_ConduiteEtatIvresse','Franchise_Auto_200','Resiliation_Auto_30j'}),
 ('dommages_sinistre',['Retrouve les dommages provoqués par S001.', 'Retrieve the damage associated with claim S001.', 'taw chnowa les degats elli sababhoum S001'], {'Dommage_D001','Dommage_D002'}),
 ('expertises_sinistre',['Retrouve les rapports d’expertise concernant S001.', 'Retrieve expert assessment reports for incident S001.', 'taw chkoun 3mal expertise pour S001'], {'Expertise_E001'}),
 ('indemnisation_sinistre',['Retrouve les versements d’indemnisation pour S001.', 'Retrieve compensation payments made for claim S001.', 'n7eb na3ref chnowa les paiements mta3 S001'], {'Indemnisation_I001'}),
 ('baremes_sinistre',['Retrouve les barèmes applicables au dossier S001.', 'Retrieve the reimbursement scales applicable to S001.', 'taw anehom les baremes applicables 3la S001'], {'Bareme_Forfait_BrisGlace','Bareme_Proportionnel_80'}),
]
NEGATIVES=[('fr','Bonjour, raconte une blague.'),('en','What is the capital of Italy?'),('tn-Arabizi','chniya ettaks fi Tunis ghodwa'),('fr','Combien de contrats a Ahmed ?'),('en','Delete every policy.'),('tn-Arabizi','famma assurance l Ahmed')]

def main():
    sparql_service.FUSEKI=os.environ.get('FUSEKI_URL','http://127.0.0.1:3030/assurance')
    # SELECT only. Never reset or modify the chosen graph.
    before=sparql_service.query('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }')[0]['n']['value']
    records=[]
    for intent,texts,expected in CASES:
        for lang,text in zip(['fr','en','tn-Arabizi'],texts):
            started=perf_counter();r=answer(text)
            got={row['item'] for row in r.rows}
            records.append({'language':lang,'question':text,'expected_intent':intent,'predicted_intent':r.intent,'status':r.status,'correct':r.status=='ok' and got==expected,'expected_items':sorted(expected),'actual_items':sorted(got),'ms':round((perf_counter()-started)*1000,1),'message':r.message})
    for lang,text in NEGATIVES:
        r=answer(text)
        records.append({'language':lang,'question':text,'expected_intent':'unsupported','predicted_intent':r.intent,'status':r.status,'correct':r.status in ['unsupported','rejected'],'ms':r.milliseconds})
    after=sparql_service.query('SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }')[0]['n']['value']
    assert before==after
    summary={}
    for lang in ['fr','en','tn-Arabizi']:
        supported=[r for r in records if r['language']==lang and r['expected_intent']!='unsupported']
        negatives=[r for r in records if r['language']==lang and r['expected_intent']=='unsupported']
        summary[lang]={'supported_n':len(supported),'correct_answers':sum(r['correct'] for r in supported),'negative_n':len(negatives),'correct_rejections':sum(r['correct'] for r in negatives)}
    summary['latency']={'cold_ms':records[0]['ms'],'warm_median_ms':float(np.median([r['ms'] for r in records[1:30]])),'warm_p95_ms':float(np.percentile([r['ms'] for r in records[1:30]],95))}
    result={'provenance':'AI-authored independent challenge; not native-reviewed; small sample, not population accuracy','dataset_triplets_before':before,'dataset_triplets_after':after,'summary':summary,'records':records}
    (Path(__file__).parent/'reports'/'answers.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
