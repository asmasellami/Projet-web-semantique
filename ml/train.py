"""Train candidates; select on validation ONLY; then evaluate frozen selection on test."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app.multilingual.text import classifier_text
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib

ROOT=Path(__file__).parent
MODEL='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
MODEL_REVISION='e8f8c211226b894fcb81acc59f3b34ba3efd5f42'

def metrics(rows,probs,labels,threshold,margin=0):
    order=np.argsort(-probs,axis=1); preds=[]
    for i,rank in enumerate(order):
        label=labels[rank[0]]
        if probs[i,rank[0]]<threshold or probs[i,rank[0]]-probs[i,rank[1]]<margin:
            label='unsupported'
        preds.append(label)
    result={}
    for language in ['all','fr','en','tn-Arabizi']:
        ids=[i for i,r in enumerate(rows) if language=='all' or r['language']==language]
        ys=[rows[i]['intent'] for i in ids]; ps=[preds[i] for i in ids]
        supported=[i for i in ids if rows[i]['intent']!='unsupported']; negative=[i for i in ids if rows[i]['intent']=='unsupported']
        result[language]={'n':len(ids),'accuracy':accuracy_score(ys,ps),'macro_f1':f1_score(ys,ps,average="macro",zero_division=0),'supported_accuracy':sum(preds[i]==rows[i]['intent'] for i in supported)/max(1,len(supported)),'rejection_rate':sum(preds[i]=='unsupported' for i in negative)/max(1,len(negative)),'coverage':sum(preds[i]!='unsupported' for i in supported)/max(1,len(supported))}
    return result,preds

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--transformers',action='store_true'); args=parser.parse_args()
    records=[json.loads(line) for line in (ROOT/'data/questions.jsonl').read_text(encoding='utf-8').splitlines()]
    sets={s:[r for r in records if r['split']==s] for s in ['train','validation','test']}
    groups=[{r['group'] for r in sets[s]} for s in sets]
    assert not any(groups[i]&groups[j] for i in range(3) for j in range(i))
    xs={s:[classifier_text(r['text']) for r in rows] for s,rows in sets.items()}
    ys={s:[r['intent'] for r in rows] for s,rows in sets.items()}
    artifacts=ROOT/'artifacts';artifacts.mkdir(exist_ok=True)
    reports=ROOT/'reports';reports.mkdir(exist_ok=True)
    candidates=[]
    started=time.perf_counter()
    clf=Pipeline([('features',FeatureUnion([('word',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True))])),('classifier',LogisticRegression(C=8,max_iter=1500,class_weight='balanced',random_state=42))])
    clf.fit(xs['train'],ys['train']);joblib.dump(clf,artifacts/'tfidf.joblib')
    candidates.append(dict(name='TF-IDF + logistic regression',engine='tfidf',path='artifacts/tfidf.joblib',labels=list(clf.classes_),validation=clf.predict_proba(xs['validation']),test=lambda:clf.predict_proba(xs['test']),training_seconds=time.perf_counter()-started))
    if args.transformers:
        import torch
        torch.set_num_threads(4)
        from sentence_transformers import SentenceTransformer
        print('Loading multilingual encoder',flush=True)
        started=time.perf_counter();encoder=SentenceTransformer(MODEL,revision=MODEL_REVISION,device='cpu');encoder.max_seq_length=64
        embeddings=encoder.encode(xs['train'],batch_size=16,show_progress_bar=True)
        frozen=LogisticRegression(C=8,max_iter=1500,class_weight='balanced',random_state=42).fit(embeddings,ys['train'])
        vp=frozen.predict_proba(encoder.encode(xs['validation'],batch_size=16));tp=frozen.predict_proba(encoder.encode(xs['test'],batch_size=16))
        candidates.append(dict(name='Frozen MiniLM + logistic regression',engine='frozen',path='artifacts/frozen',labels=list(frozen.classes_),validation=vp,test=lambda:tp,training_seconds=time.perf_counter()-started))
        joblib.dump(frozen,artifacts/'frozen-head.joblib');encoder.save(str(artifacts/'frozen'))
        del encoder
        from setfit import SetFitModel,Trainer,TrainingArguments
        from datasets import Dataset
        labels=sorted(set(ys['train']));label_ids={l:i for i,l in enumerate(labels)}
        started=time.perf_counter(); model=SetFitModel.from_pretrained(str(artifacts/'frozen'),labels=labels);model.model_body.max_seq_length=64
        dataset=Dataset.from_dict({'text':xs['train'],'label':[label_ids[y] for y in ys['train']]})
        arguments=TrainingArguments(output_dir=str(ROOT/'checkpoints'),batch_size=(8,16),num_epochs=(1,10),max_steps=40,num_iterations=2,max_length=64,seed=42,report_to='none',logging_steps=10)
        trainer=Trainer(model=model,args=arguments,train_dataset=dataset)
        trainer.train(); model.save_pretrained(str(artifacts/'setfit'))
        vp=np.asarray(model.predict_proba(xs['validation']));tp_set=np.asarray(model.predict_proba(xs['test']))
        candidates.append(dict(name='Fine-tuned SetFit MiniLM',engine='setfit',path='artifacts/setfit',labels=labels,validation=vp,test=lambda:tp_set,training_seconds=time.perf_counter()-started))
    # No test labels are used in candidate or threshold selection.
    summary=[]
    for c in candidates:
        options=[]
        for threshold in [.15,.2,.25,.3,.4,.5,.6]:
            for margin in [0,.05,.1]:
                m,_=metrics(sets['validation'],c['validation'],c['labels'],threshold,margin)
                score=np.mean([m[l]['macro_f1'] for l in ['fr','en','tn-Arabizi']])
                options.append((score,threshold,margin,m))
        score,threshold,margin,validation=max(options,key=lambda x:x[0])
        c.update(threshold=threshold,margin=margin,selection_score=score)
        summary.append({k:v for k,v in c.items() if k not in ['validation','test','labels'] }|{'validation':validation})
    winner=max(candidates,key=lambda c:(c['selection_score'],c['engine']=='tfidf'))
    config={k:winner[k] for k in ['name','engine','path','threshold','margin']}
    if config['engine']=='frozen':
        config['head']='artifacts/frozen-head.joblib'
    (artifacts/'selected.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    tests={}
    for c in candidates:
        m,preds=metrics(sets['test'],c['test'](),c['labels'],c['threshold'],c['margin'])
        tests[c['name']]=m
        errors=[{'id':r['id'],'text':r['text'],'expected':r['intent'],'predicted':p} for r,p in zip(sets['test'],preds) if r['intent']!=p]
        (reports/(c['engine']+'-test-errors.json')).write_text(json.dumps(errors,ensure_ascii=False,indent=2),encoding='utf-8')
    result={'seed':42,'counts':{s:len(r) for s,r in sets.items()},'provenance':'AI-authored templated seed corpus; no native review; results are internal benchmarks, not validated population accuracy','candidates':summary,'selected':config,'test':tests}
    (reports/'classification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)
if __name__=='__main__':main()
