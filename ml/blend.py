"""One additional validation-only experiment: blend the already-trained candidates.

Initial aggregate test results motivated this experiment; they are retained as stage1.
No test labels or challenge answers choose blend weights or thresholds.
"""
import json
import shutil
import sys
from pathlib import Path
import numpy as np
import joblib
import torch
torch.set_num_threads(4)
from setfit import SetFitModel
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.multilingual.text import classifier_text
from ml.train import metrics

ROOT=Path(__file__).parent
def main():
    report=ROOT/'reports/classification.json'
    shutil.copyfile(report,ROOT/'reports/classification-stage1.json')
    rows=[json.loads(l) for l in (ROOT/'data/questions.jsonl').read_text(encoding='utf-8').splitlines()]
    val=[r for r in rows if r['split']=='validation'];test=[r for r in rows if r['split']=='test']
    tfidf=joblib.load(ROOT/'artifacts/tfidf.joblib')
    model=SetFitModel.from_pretrained(str(ROOT/'artifacts/setfit'),local_files_only=True)
    labels=list(tfidf.classes_);assert labels==model.labels
    texts=[classifier_text(r['text']) for r in val]
    a=tfidf.predict_proba(texts);b=np.asarray(model.predict_proba(texts))
    candidates=[]
    for weight in [0,.25,.5,.75,1]:
        for threshold in [.15,.2,.25,.3,.4,.5,.6]:
            for margin in [0,.05,.1]:
                m,_=metrics(val,weight*a+(1-weight)*b,labels,threshold,margin)
                score=np.mean([m[l]['macro_f1'] for l in ['fr','en','tn-Arabizi']])
                candidates.append((score,weight,threshold,margin,m))
    score,weight,threshold,margin,validation=max(candidates,key=lambda c:(c[0],c[1]))
    result=json.loads(report.read_text(encoding='utf-8'))
    previous=max(c['selection_score'] for c in result['candidates'])
    config={'name':'TF-IDF + fine-tuned MiniLM blend','engine':'ensemble','path':'artifacts/setfit','tfidf':'artifacts/tfidf.joblib','weight':weight,'threshold':threshold,'margin':margin}
    (ROOT/'reports/blend-validation.json').write_text(json.dumps({'selection_score':score,'weight':weight,'threshold':threshold,'margin':margin,'validation':validation,'development_history':'additional experiment after stage1 aggregate tests; choices use validation only'},indent=2),encoding='utf-8')
    if score>previous and 0<weight<1:
        (ROOT/'artifacts/selected.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
        result['selected']=config
    texts=[classifier_text(r['text']) for r in test]
    m,preds=metrics(test,weight*tfidf.predict_proba(texts)+(1-weight)*np.asarray(model.predict_proba(texts)),labels,threshold,margin)
    result['candidates'].append({'name':config['name'],'selection_score':score,'weight':weight,'threshold':threshold,'margin':margin,'validation':validation})
    result['test'][config['name']]=m
    result['evaluation_history']='Stage1 test results inspected before adding a validation-tuned blend; same development test reused for reporting. Fresh human-reviewed external evaluation still required.'
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'selected':result['selected'],'validation':validation,'test':m},indent=2))
if __name__=='__main__':main()
