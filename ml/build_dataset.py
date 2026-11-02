"""Reproducible AI-authored seed corpus. Templates/translations/name variants never cross splits.

NOT a native-reviewed language benchmark. See data/README.md before interpreting scores.
"""
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

DATA = {
'biens_assure': [
['Quels biens sont assurés pour {x} ?', 'Montre les biens de {x}', 'Liste les actifs assurés de {x}', 'Je cherche les véhicules assurés pour {x}', 'Quels logements sont couverts pour {x} ?', 'Affiche le patrimoine assuré de {x}', 'Les biens associés à {x}', 'Quelles possessions appartiennent à {x} ?', 'Que possède {x} ?', 'Je voudrais consulter les biens couverts par les contrats de {x}'],
['Which assets are insured for {x}?','Show the assets of {x}','List insured property belonging to {x}','I need the insured vehicles of {x}','Which homes are covered for {x}?','Display insured possessions for {x}','Assets associated with {x}','What property does {x} own?','What does {x} own?','I would like the assets covered by policies held by {x}'],
['chniya les biens assures mta3 {x}','warini les biens mta3 {x}','a3tini les proprietes assurees mta3 {x}','n7eb nchouf les voitures assurees mta3 {x}','les dyar couvertes mta3 {x} chnowa','affichili patrimoine assure mta3 {x}','les biens elli marboutin b {x}','chnowa les biens elli yomlek {x}','{x} chnowa yomlek','n7eb les biens couverts bel contrats mta3 {x}']],
'assures_compagnie': [
['Quels sont les assurés de {x} ?', 'Montre les clients de la compagnie {x}', 'Liste les personnes assurées chez {x}', 'Qui est assuré auprès de {x} ?', 'Je cherche les souscripteurs de {x}', 'Affiche les adhérents de {x}', 'La clientèle assurée par {x}', 'Quels clients ont une assurance chez {x} ?', 'Les personnes couvertes par des contrats de {x}', 'Je voudrais consulter les clients assurés par {x}'],
['Who is insured by {x}?','Show customers of insurer {x}','List people insured with {x}','Who has insurance with {x}?','Find policyholders of {x}','Display clients covered by {x}','The insured customer base of {x}','Which customers have insurance at {x}?','People holding policies issued by {x}','I would like the customers insured by {x}'],
['chkoun assure 3and {x}','warini les clients mta3 compagnie {x}','a3tini les assures 3and {x}','chkoun 3andou assurance chez {x}','nlawej 3al souscripteurs mta3 {x}','affichili les adherents mta3 {x}','clientele assuree mta3 {x}','anehom les clients elli assures chez {x}','les personnes elli 3andhom contrat m3a {x}','n7eb nchouf les clients assures par {x}']],
'contrats_assure': [
['Quels sont les contrats de {x} ?', 'Montre les polices souscrites par {x}', 'Liste les assurances de {x}', 'Quels contrats a souscrit {x} ?', 'Je cherche les contrats d’assurance de {x}', 'Affiche les polices du client {x}', 'Les contrats associés à {x}', 'Sous quelles polices est assuré {x} ?', 'Les contrats détenus par {x}', 'Je voudrais consulter les polices de {x}'],
['Which policies does {x} hold?','Show insurance contracts taken out by {x}','List insurance policies for {x}','What contracts has {x} signed?','Find insurance contracts of {x}','Display policies held by customer {x}','Contracts associated with {x}','Under which policies is {x} insured?','Policies subscribed to by {x}','I would like the insurance contracts of {x}'],
['chnowa les contrats mta3 {x}','warini les polices souscrites par {x}','a3tini les assurances mta3 {x}','{x} anehom les contrats elli souscrit fihom','nlawej 3al contrats assurance mta3 {x}','affichili les polices mta3 client {x}','les contrats marboutin b {x}','{x} assure b anehom les polices','les contrats elli 3and {x}','n7eb nchouf les contrats mta3 {x}']],
'sinistres_filtres': [
['Quels sinistres ont eu lieu à {x} ?', 'Montre les sinistres à {x}', 'Liste les dossiers de sinistre à {x}', 'Les accidents déclarés à {x}', 'Je cherche les sinistres survenus à {x}', 'Affiche les incidents enregistrés à {x}', 'Quels dossiers concernent un sinistre à {x} ?', 'Les sinistres indemnisés à {x}', 'Les sinistres en expertise à {x}', 'Je voudrais consulter les sinistres à {x}'],
['Which claims occurred in {x}?','Show claims in {x}','List claim files located in {x}','Declared accidents in {x}','Find insurance claims occurring in {x}','Display incidents recorded in {x}','Which claim files concern events in {x}?','Compensated claims in {x}','Claims under assessment in {x}','I would like the claims in {x}'],
['chniya les sinistres elli sarou fi {x}','warini les sinistres fi {x}','a3tini dossiers sinistres fi {x}','les accidents declares fi {x}','nlawej 3al sinistres elli sarou fi {x}','affichili les incidents fi {x}','anehom dossiers sinistres fi {x}','les sinistres indemnises fi {x}','les sinistres en expertise fi {x}','n7eb nchouf les sinistres fi {x}']],
'garanties_contrat': [
['Quelles garanties inclut le contrat {x} ?', 'Montre les garanties du contrat {x}', 'Liste les couvertures prévues dans {x}', 'Quels risques sont couverts par {x} ?', 'Je cherche les garanties incluses dans {x}', 'Affiche la couverture du contrat {x}', 'Les protections offertes par la police {x}', 'Quelles garanties figurent dans {x} ?', 'La liste des garanties associées à {x}', 'Je voudrais consulter les garanties de {x}'],
['Which guarantees are included in policy {x}?','Show guarantees of contract {x}','List coverage provided by {x}','What risks are covered by policy {x}?','Find guarantees included in {x}','Display coverage for policy {x}','Protections provided by insurance contract {x}','Which coverage options belong to {x}?','The guarantees attached to {x}','I would like coverage details of policy {x}'],
['chniya les garanties fi contrat {x}','warini les garanties mta3 contrat {x}','a3tini les couvertures fi {x}','anehom risques couverts bel contrat {x}','nlawej 3al garanties incluses fi {x}','affichili couverture mta3 contrat {x}','les protections elli ya3tihom contrat {x}','chniya les garanties elli mawjouda fi {x}','liste garanties marboutin b {x}','n7eb nchouf garanties mta3 {x}']],
'clauses_contrat': [
['Quelles clauses contient le contrat {x} ?', 'Montre les clauses de {x}', 'Liste les conditions contractuelles de {x}', 'Quelles exclusions sont prévues par {x} ?', 'Je cherche les clauses légales de {x}', 'Affiche les franchises et clauses de {x}', 'Les dispositions du contrat {x}', 'Quelles conditions figurent dans la police {x} ?', 'Les clauses associées à {x}', 'Je voudrais consulter les conditions de {x}'],
['Which clauses are in contract {x}?','Show clauses of {x}','List contractual conditions of {x}','Which exclusions are specified in {x}?','Find legal clauses of {x}','Display deductibles and clauses of {x}','Provisions of insurance policy {x}','What conditions appear in policy {x}?','Clauses attached to {x}','I would like the terms of contract {x}'],
['chniya les clauses fi contrat {x}','warini les clauses mta3 {x}','a3tini les conditions contractuelles mta3 {x}','anehom exclusions fi {x}','nlawej 3al clauses legales mta3 {x}','affichili franchises w clauses mta3 {x}','les dispositions mta3 contrat {x}','chniya les conditions fi police {x}','les clauses marboutin b {x}','n7eb nchouf conditions mta3 contrat {x}']],
'dommages_sinistre': [
['Quels dommages a causés {x} ?', 'Montre les dommages du sinistre {x}', 'Liste les dégâts liés à {x}', 'Quels préjudices résultent de {x} ?', 'Je cherche les dommages causés par {x}', 'Affiche les dégâts du dossier {x}', 'Les dommages associés au sinistre {x}', 'Quelles dégradations viennent de {x} ?', 'Les descriptions des dommages de {x}', 'Je voudrais consulter les dégâts de {x}'],
['What damage was caused by {x}?','Show damage for claim {x}','List losses linked to {x}','What harm resulted from {x}?','Find damage caused by {x}','Display damage recorded for claim {x}','Damage associated with incident {x}','Which injuries or damage resulted from {x}?','Descriptions of damage for {x}','I would like the damage details of {x}'],
['chniya les dommages mta3 {x}','warini les dommages mta3 sinistre {x}','a3tini les degats lies b {x}','chnowa les prejudices elli sarou mel {x}','nlawej 3al dommages elli sababhoum {x}','affichili les degats mta3 dossier {x}','les dommages marboutin b sinistre {x}','anehom les degats elli sarou mel {x}','description dommages mta3 {x}','n7eb nchouf les degats mta3 {x}']],
'expertises_sinistre': [
['Quelles expertises concernent {x} ?', 'Montre les rapports d’expertise du sinistre {x}', 'Liste les évaluations de {x}', 'Quel expert a évalué le sinistre {x} ?', 'Je cherche les expertises du dossier {x}', 'Affiche les rapports des experts pour {x}', 'Les expertises associées à {x}', 'Qui a effectué l’expertise de {x} ?', 'Les évaluations techniques du sinistre {x}', 'Je voudrais consulter les expertises de {x}'],
['Which assessments concern {x}?','Show expert reports for claim {x}','List assessments of {x}','Which expert assessed claim {x}?','Find expert assessments for file {x}','Display expert reports about {x}','Expert assessments linked to {x}','Who performed the assessment of {x}?','Technical assessments for incident {x}','I would like the expert reports for {x}'],
['chniya les expertises mta3 {x}','warini rapports expertise mta3 sinistre {x}','a3tini les evaluations mta3 {x}','anehou expert 9ayem sinistre {x}','nlawej 3al expertises mta3 dossier {x}','affichili rapports experts pour {x}','les expertises marboutin b {x}','chkoun 3mal expertise mta3 {x}','les evaluations techniques mta3 sinistre {x}','n7eb nchouf les expertises mta3 {x}']],
'indemnisation_sinistre': [
['Quelle indemnisation pour {x} ?', 'Montre les paiements du sinistre {x}', 'Liste les indemnisations liées à {x}', 'Quel montant a été versé pour {x} ?', 'Je cherche les règlements du dossier {x}', 'Affiche les indemnités de {x}', 'Les compensations associées à {x}', 'Combien a été payé pour {x} ?', 'Les versements effectués pour le sinistre {x}', 'Je voudrais consulter les paiements de {x}'],
['What compensation was paid for {x}?','Show payments for claim {x}','List compensation linked to {x}','What amount was paid for {x}?','Find settlements for claim {x}','Display indemnities for {x}','Compensation associated with {x}','How much was paid for {x}?','Payments made for incident {x}','I would like the payment details of {x}'],
['chniya indemnisation mta3 {x}','warini les paiements mta3 sinistre {x}','a3tini les indemnisations lies b {x}','9adech tkhalles pour {x}','nlawej 3al reglements mta3 dossier {x}','affichili les indemnites mta3 {x}','les compensations marboutin b {x}','9addesh khallsou pour {x}','les versements mta3 sinistre {x}','n7eb nchouf les paiements mta3 {x}']],
'baremes_sinistre': [
['Quel barème s’applique à {x} ?', 'Montre les barèmes du sinistre {x}', 'Liste les grilles d’indemnisation pour {x}', 'Selon quel barème indemniser {x} ?', 'Je cherche le barème applicable à {x}', 'Affiche les échelles de remboursement de {x}', 'Les barèmes associés au sinistre {x}', 'Quelles grilles sont utilisées pour {x} ?', 'Les références de barème pour {x}', 'Je voudrais consulter les barèmes applicables à {x}'],
['Which compensation scale applies to {x}?','Show scales for claim {x}','List compensation schedules applicable to {x}','Under which scale is {x} compensated?','Find the applicable compensation schedule for {x}','Display reimbursement scales for {x}','Compensation scales associated with claim {x}','Which assessment schedules are used for {x}?','Scale references applicable to {x}','I would like the compensation scales for {x}'],
['anehou bareme yettaba9 3la {x}','warini les baremes mta3 sinistre {x}','a3tini les grilles indemnisation pour {x}','b anehou bareme y3awdhou {x}','nlawej 3al bareme applicable l {x}','affichili echelles remboursement mta3 {x}','les baremes marboutin b sinistre {x}','anehom grilles elli yesta3mlouhom pour {x}','references bareme mta3 {x}','n7eb nchouf baremes applicables 3la {x}']]
}
NAMES = {'biens_assure':['Ahmed','Salma','Youssef'], 'contrats_assure':['Ahmed','Salma','Youssef'], 'assures_compagnie':['AssurTunis','MedAssur','GlobalRe'], 'sinistres_filtres':['Tunis','Ariana','Sousse'], 'garanties_contrat':['AUTO-2026-001','HAB-2026-014','SANTE-2026-031'],'clauses_contrat':['AUTO-2026-001','HAB-2026-014','SANTE-2026-031']}
NEGATIVES = [
['Quel temps fait-il demain ?','What is the weather tomorrow?','kifech bech ykoun ettaks ghodwa'],
['Écris une histoire','Write a story','ektebli 7keya'],
['Supprime le contrat AUTO-2026-001','Delete policy AUTO-2026-001','fassa5 contrat AUTO-2026-001'],
['Crée une assurance pour Ahmed','Create insurance for Ahmed','a3mel assurance l Ahmed'],
['Combien de contrats a Ahmed ?','How many policies does Ahmed have?','9adech men contrat 3and Ahmed'],
['Est-ce que Ahmed est assuré ?','Does Ahmed have insurance?','famma assurance l Ahmed'],
['Compare Ahmed et Salma','Compare Ahmed and Salma','9aren Ahmed w Salma'],
['Calcule automatiquement ma prime','Calculate my premium automatically','e7sebli prime assurance'],
['Donne des conseils juridiques','Give legal advice','a3tini conseil juridique'],
['Réserve un restaurant','Book a restaurant','reserverli restaurant'],
['Modifie le nom de Ahmed','Change the name of Ahmed','baddel esm Ahmed'],
['Annule ma police','Cancel my policy','annulili contrat mte3i'],
['Envoie un email à MedAssur','Send an email to MedAssur','ab3ath email l MedAssur'],
['Achète une assurance auto','Buy car insurance','echrili assurance karhba'],
['Prédis les accidents futurs','Predict future accidents','tawa9a3 les accidents jeyin'],
['Traduis un poème en arabe','Translate a poem into Arabic','tarjemli chi3r bel 3arbi'],
['Combien de véhicules possède Salma ?','How many vehicles does Salma own?','9adech men karhba 3and Salma'],
['Existe-t-il un contrat pour Youssef ?','Is there a policy for Youssef?','famma contrat l Youssef'],
['Qui gagnera le match ?','Who will win the match?','chkoun bech yerba7 el match'],
['Calcule une prime pour une nouvelle voiture','Calculate a premium for a new car','e7sebli prime karhba jdida'],
['Rédige un contrat juridique','Draft a legal contract','ektebli contrat juridique'],
['Mets à jour le montant de S001','Update the amount of S001','baddel montant mta3 S001'],
['Rembourse Ahmed immédiatement','Refund Ahmed immediately','raja3 flous Ahmed taw'],
['Connecte-toi à mon compte','Log into my account','od5ol compte mte3i'],
['Télécharge tous mes emails','Download all my emails','habbet les emails mte3i'],
['Montre les résultats sportifs','Show sports results','warini resultat sport'],
['Donne une recette de cuisine','Give me a cooking recipe','a3tini recette makla'],
['Explique les trous noirs','Explain black holes','fassarli les trous noirs'],
['Combien de sinistres sont à Tunis ?','How many claims are in Tunis?','9adech men sinistre fi Tunis'],
['Compare les tarifs des compagnies','Compare insurer prices','9aren les tarifs mta3 compagnies']]

def main():
    out=Path(__file__).parent/'data';out.mkdir(parents=True,exist_ok=True)
    records=[]
    for label,languages in DATA.items():
        for lang,patterns in zip(['fr','en','tn-Arabizi'],languages):
            for i,pattern in enumerate(patterns):
                split='train' if i<6 else 'validation' if i<8 else 'test'
                for j,name in enumerate(NAMES.get(label,['S001','S002','S003'])):
                    records.append(dict(id=f'{label}-{lang}-{i}-{j}',text=pattern.format(x=name),language=lang,intent=label,entity=name,group=f'{label}-pattern-{i}',split=split,provenance='AI-authored seed template',native_reviewed=False))
    for i,phrases in enumerate(NEGATIVES):
        for lang,text in zip(['fr','en','tn-Arabizi'],phrases):
            records.append(dict(id=f'negative-{lang}-{i}',text=text,language=lang,intent='unsupported',entity='',group=f'negative-topic-{i}',split='train' if i%10<6 else 'validation' if i%10<8 else 'test',provenance='AI-authored',native_reviewed=False))
    (out/'questions.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf-8')
    groups={}
    for r in records:
        if r['group'] in groups:assert groups[r['group']]==r['split']
        groups[r['group']]=r['split']
    print('Saved',len(records),'examples;',len(groups),'disjoint source groups')
if __name__=='__main__':main()
