"""Train expanded discovery/reverse-relationship labels. UX audit prompts remain outside training."""
import json
import sys
from pathlib import Path
import numpy as np
import joblib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from sklearn.pipeline import Pipeline,FeatureUnion
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from app.multilingual.text import classifier_text
from ml.train import metrics

ROOT=Path(__file__).parent
NEW={
 'policy_assets':[
 ['Biens du contrat {x}','Quels objets couvre {x} ?','Les propriétés couvertes par la police {x}','Consulte les biens du contrat {x}','Affiche les biens couverts par {x}'],
 ['Assets of policy {x}','What property does {x} cover?','Insured objects covered by contract {x}','Read assets of contract {x}','Display property covered by {x}'],
 ['les biens mta3 contrat {x}','chnowa yghatti contrat {x}','les proprietes couvertes bel police {x}','n7eb biens mta3 contrat {x}','affichili biens couverts b {x}']],
 'policy_claims':[
 ['Sinistres du contrat {x}','Quels incidents concernent {x} ?','Les dossiers associés à la police {x}','Consulte les sinistres du contrat {x}','Affiche les sinistres liés à {x}'],
 ['Claims of policy {x}','What incidents concern contract {x}?','Claim files associated with policy {x}','Read claims for contract {x}','Display claims linked to {x}'],
 ['les sinistres mta3 contrat {x}','chnowa les incidents mta3 contrat {x}','les dossiers marboutin bel police {x}','n7eb sinistres mta3 contrat {x}','affichili sinistres lies b {x}']],
 'insurer_policies':[
 ['Contrats de la compagnie {x}','Quelles polices émet {x} ?','Les contrats émis par {x}','Consulte les contrats de l’assureur {x}','Affiche les polices de la compagnie {x}'],
 ['Policies of insurer {x}','Which contracts does {x} issue?','Contracts issued by {x}','Read policies of insurance company {x}','Display policies of the insurer {x}'],
 ['les contrats mta3 compagnie {x}','anehom polices elli temet {x}','les contrats emis par {x}','n7eb contrats mta3 assureur {x}','affichili polices mta3 compagnie {x}']],
 'list_customers':[
 ['Affiche le répertoire des clients','Quels assurés sont enregistrés ?','Je veux parcourir les clients','Présente la clientèle','Les noms des clients disponibles'],
 ['Display the customer directory','Which insured people are registered?','Let me browse customers','Present the customer base','Names of available customers'],
 ['affichili repertoire clients','anehom les assures enregistrin','n7eb netfarrej fel clients','a3tini clientele elli mawjouda','esmiyet les clients disponibles']],
 'list_insurers':[
 ['Affiche le répertoire des assureurs','Quelles compagnies sont enregistrées ?','Je veux parcourir les assureurs','Présente les sociétés d’assurance','Les noms des compagnies disponibles'],
 ['Display the insurer directory','Which insurers are registered?','Let me browse insurers','Present the insurance firms','Names of available insurance companies'],
 ['affichili repertoire compagnies','anehom les assureurs enregistrin','n7eb netfarrej fel compagnies','a3tini les societes assurance','esmiyet compagnies disponibles']],
 'list_policies':[
 ['Affiche le répertoire des polices','Quels contrats sont enregistrés ?','Je veux parcourir tous les contrats','Présente toutes les polices','Les contrats disponibles dans la base'],
 ['Display the policy directory','Which contracts are registered?','Let me browse every policy','Present every insurance contract','Available contracts in the database'],
 ['affichili repertoire contrats','anehom les contrats enregistrin','n7eb netfarrej fel contrats elkol','a3tini les polices elkol','les contrats disponibles fel base']],
 'list_assets':[
 ['Affiche le répertoire des biens','Quels biens assurés sont enregistrés ?','Je veux parcourir les biens','Présente toutes les propriétés assurées','Les biens disponibles dans la base'],
 ['Display the asset directory','Which insured assets are registered?','Let me browse insured property','Present every insured asset','Available assets in the database'],
 ['affichili repertoire biens','anehom les biens enregistrin','n7eb netfarrej fel biens','a3tini les proprietes assurees elkol','les biens disponibles fel base']],
 'owner_vehicle':[
 ['Retrouve le propriétaire de {x}','Qui est le propriétaire du véhicule {x} ?','À quel assuré appartient {x} ?','Le nom du propriétaire de {x}','Identifie la personne qui possède {x}'],
 ['Find the owner of {x}','Who is the owner of vehicle {x}?','Which customer owns {x}?','The owner name for {x}','Identify the person who owns {x}'],
 ['lawwejli 3al proprietaire mta3 {x}','chkoun proprietaire mta3 karhba {x}','anehou assure yomlek {x}','esm proprietaire mta3 {x}','a3refli chkoun yomlek {x}']],
 'policies_vehicle':[
 ['Retrouve les polices couvrant {x}','Quels contrats assurent {x} ?','Les contrats associés au véhicule {x}','Cherche la couverture contractuelle de {x}','Affiche les polices qui couvrent {x}'],
 ['Find policies covering {x}','What contracts insure {x}?','Contracts linked to vehicle {x}','Find contractual coverage of {x}','Display the policies that cover {x}'],
 ['lawwejli les polices elli yghattiw {x}','anehom contrats yassuriw {x}','les contrats marboutin bel karhba {x}','lawwej couverture contractuelle mta3 {x}','affichili polices elli yghattiw {x}']],
 'issuer_policy':[
 ['Retrouve l’assureur émetteur de {x}','Qui a émis la police {x} ?','La société émettrice du contrat {x}','Quelle compagnie assure le contrat {x} ?','Affiche l’assureur du contrat {x}'],
 ['Find the issuing insurer of {x}','Who issued insurance contract {x}?','The issuing firm for policy {x}','Which insurer issued contract {x}?','Display the insurer of policy {x}'],
 ['lawwejli assureur emetteur mta3 {x}','chkoun emet contrat {x}','societe emettrice mta3 {x}','anehi compagnie 3amlet contrat {x}','affichili assureur mta3 contrat {x}']],
 'holder_policy':[
 ['Retrouve le souscripteur de {x}','Qui détient la police {x} ?','Le client associé au contrat {x}','Quel assuré a signé {x} ?','Affiche le titulaire du contrat {x}'],
 ['Find the policyholder of {x}','Who holds insurance contract {x}?','The customer linked to policy {x}','Which insured customer signed {x}?','Display the holder of contract {x}'],
 ['lawwejli souscripteur mta3 {x}','chkoun detient police {x}','client marbout b contrat {x}','anehou assure signe {x}','affichili titulaire mta3 contrat {x}']],
 'claim_details':[
 ['Affiche la fiche du sinistre {x}','Je cherche le dossier {x}','Consulte les détails du sinistre {x}','Retrouve les informations de {x}','Le statut et le lieu de {x}'],
 ['Display the record for claim {x}','Find incident file {x}','Read the details of claim {x}','Retrieve information on claim {x}','The status and location of claim {x}'],
 ['affichili fiche sinistre {x}','nlawej 3al dossier {x}','n7eb details sinistre {x}','lawwej informations mta3 sinistre {x}','statut w lieu mta3 sinistre {x}']],
 'customer_claims':[
 ['Retrouve les dossiers de sinistre du client {x}','Les sinistres liés aux contrats de {x}','Consulte les incidents de {x}','Quels sinistres concernent l’assuré {x} ?','Affiche les sinistres associés à {x}'],
 ['Find claim files belonging to customer {x}','Claims linked to policies of {x}','Read the incidents of {x}','Which claims involve insured customer {x}?','Display claims associated with {x}'],
 ['lawwej dossiers sinistres mta3 client {x}','les sinistres lies bel contrats mta3 {x}','n7eb incidents mta3 {x}','anehom sinistres yhemmou assure {x}','affichili sinistres marboutin b {x}']],
}

def main():
    rows=[json.loads(l) for l in (ROOT/'data/questions.jsonl').read_text(encoding='utf-8').splitlines()]
    audit=json.loads((ROOT/'reports/exploration-audit.json').read_text(encoding='utf-8'))
    forbidden={classifier_text(r['question']) for r in audit['records']}
    extra=[]
    for label,versions in NEW.items():
        names=['123 TU 4567','205 TU 8890'] if label.endswith('vehicle') else ['AUTO-2026-001','HAB-2026-014'] if label.endswith('policy') or label in ['policy_assets','policy_claims'] else ['MedAssur','AssurTunis'] if label=='insurer_policies' else ['S001','S002'] if label=='claim_details' else ['Ahmed','Salma'] if label=='customer_claims' else ['']
        for lang,patterns in zip(['fr','en','tn-Arabizi'],versions):
            for i,pattern in enumerate(patterns):
                for j,name in enumerate(names):
                    q=pattern.format(x=name)
                    if classifier_text(q) in forbidden:continue
                    extra.append(dict(id=f'conversation-{label}-{lang}-{i}-{j}',text=q,language=lang,intent=label,entity=name,group=f'conversation-{label}-{i}',split='train' if i<3 else 'validation' if i==3 else 'test',provenance='AI-authored discovery seed',native_reviewed=False))
    rows+=extra
    path=ROOT/'data/conversation-questions.jsonl'
    path.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows),encoding='utf-8')
    sets={s:[r for r in rows if r['split']==s] for s in ['train','validation','test']}
    groups=[{r['group'] for r in sets[s]} for s in sets]
    assert not any(groups[i]&groups[j] for i in range(3) for j in range(i))
    x={s:[classifier_text(r['text']) for r in values] for s,values in sets.items()}
    clf=Pipeline([('features',FeatureUnion([('word',TfidfVectorizer(ngram_range=(1,2),sublinear_tf=True)),('char',TfidfVectorizer(analyzer='char_wb',ngram_range=(3,5),sublinear_tf=True))])),('classifier',LogisticRegression(C=8,max_iter=1500,class_weight='balanced',random_state=42))])
    clf.fit(x['train'],[r['intent'] for r in sets['train']])
    p=clf.predict_proba(x['validation']);options=[]
    for threshold in [.15,.2,.25,.3,.4]:
        m,_=metrics(sets['validation'],p,clf.classes_,threshold)
        options.append((np.mean([m[l]['macro_f1'] for l in ['fr','en','tn-Arabizi']]),threshold,m))
    _,threshold,validation=max(options,key=lambda v:v[0])
    test,_=metrics(sets['test'],clf.predict_proba(x['test']),clf.classes_,threshold)
    artifact=ROOT/'artifacts/conversation-tfidf.joblib';artifact.parent.mkdir(parents=True,exist_ok=True);joblib.dump(clf,artifact)
    selected=ROOT/'artifacts/selected.json'
    previous=ROOT/'reports/selected-before-conversation.json'
    if not previous.exists() and selected.exists():previous.write_text(selected.read_text(),encoding='utf-8')
    selected.write_text(json.dumps(dict(name='Multilingual discovery classifier + relation contracts',engine='tfidf',path='artifacts/conversation-tfidf.joblib',threshold=threshold,margin=0),indent=2),encoding='utf-8')
    report=dict(seed=42,added_examples=len(extra),total_examples=len(rows),labels=list(clf.classes_),counts={k:len(v) for k,v in sets.items()},audit_prompts_added_to_training=0,validation=validation,test=test,limitations='AI-authored internal corpus; no native review; relation contracts and conversation state are evaluated separately from model-only scores.')
    (ROOT/'reports/conversation-classification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
