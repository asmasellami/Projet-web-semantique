"""Explicit relation contracts constrain the learned classifier, rather than inventing SQL/SPARQL.

Returns None for language patterns not covered here, preserving ML classification.
"""
import re
from .text import word_present

def route(text, has_entity):
    def has(words):return any(word_present(text,w) for w in words)
    policy=has(['policy','policies','contract','contracts','contrat','contrats','police','polices']) or has_entity('ContratAssurance')
    asset=has(['asset','assets','property','properties','propriete','proprietes','biens','bien','car','cars','vehicle','vehicles','vehicule','vehicules','voiture','voitures','karhba','karhabet','logement','logements','dyar'])
    claim=has(['claim','claims','sinistre','sinistres','dossier','dossiers'])
    customer=has(['user','users','customer','customers','client','clients','assures','adherents'])
    company=has(['company','companies','insurer','insurers','compagnie','compagnies','assureur','assureurs'])
    owner=has(['owner','owners','owns','own','owned','possede','appartient','proprietaire','proprietaires','yomlek']) or bool(re.search(r'\b(?:mta3?|mte3)\s+chkoun\b',text))
    who=has(['who','whose','qui','chkoun','owner','proprietaire'])
    if re.search(r'\b(what.*own|que.*possede|chnowa.*yomlek)\b',text):return 'biens_assure'
    if re.search(r'\w.+\b(and|et|w)\b',text) and sum([policy,asset,claim])>1 and not has(['cover','covers','couvrent','couvre','yghattiw']):
        raise ValueError('Posez une question à la fois / Ask one question at a time.')
    if who and (owner or (asset and has(['whose']))) and not policy:return 'owner_vehicle'
    if policy and asset and (has(['cover','covers','covering','couvre','couvrent','yghattiw']) or has_entity('BienAssure')):return 'policies_vehicle'
    reference=has(['it','its','sa','son','ses','mte3ou','mta3ou','hedha'])
    if (policy or reference) and (has(['issued','issue','emitted','emis','emet','emetteur','3amlet']) or company) and not asset:return 'issuer_policy'
    if has(['policyholder','holder','souscripteur','titulaire']) or (who and has(['holds','hold','souscrit','belongs'])):return 'holder_policy'
    if has(['guarantee','guarantees','garantie','garanties','coverage','protections','risques','risks']) and not asset:return 'garanties_contrat'
    if has(['clause','clauses','conditions','terms','exclusions','franchise','franchises','deductible','deductibles']):return 'clauses_contrat'
    if has(['bareme','baremes','scale','scales','schedule','schedules','grilles']):return 'baremes_sinistre'
    if has(['expertise','expertises','assessment','assessments','assessed','expert','experts','rapports','evaluations','evalue','9ayem']) and not (claim and has(['en expertise','under assessment','under review'])):return 'expertises_sinistre'
    if has(['damage','dommages','dommage','degats','injuries','prejudices']):return 'dommages_sinistre'
    if re.search(r'\b(how much|quel montant|combien a|9adech|9addesh)\b',text):return 'indemnisation_sinistre'
    if has(['compensation','indemnisation','indemnisations','payments','payment','paiements','paiement','indemnites','versements','reglements']):return 'indemnisation_sinistre'
    if has(['where','location','lieu','status','statut','date']) and has_entity('Sinistre'):return 'claim_details'
    if claim:
        if has_entity('Sinistre'):
            if who:raise ValueError('Précisez la relation recherchée : expert, propriétaire ou souscripteur ?')
            return 'claim_details'
        if has_entity('ContratAssurance'):return 'policy_claims'
        if has_entity('Assure'):return 'customer_claims'
        if re.search(r'\b(for|of|de|mta3|mte3)\s+\w+',text) and not has(['tous','toutes','all','lkol','elkol']):return 'customer_claims'
        return 'sinistres_filtres'
    if asset:
        if has_entity('ContratAssurance'):return 'policy_assets'
        return 'list_assets' if global_listing(text,has_entity('Assure')) else 'biens_assure'
    if policy:
        if has_entity('CompagnieAssurance'):return 'insurer_policies'
        return 'list_policies' if global_listing(text,has_entity('Assure')) else 'contrats_assure'
    if customer:
        if has_entity('Assure') and not has_entity('CompagnieAssurance'):
            raise ValueError('Sélectionnez ce client ou demandez ses contrats, ses biens ou ses sinistres.')
        return 'assures_compagnie' if has_entity('CompagnieAssurance') or not global_listing(text,False) else 'list_customers'
    if company and not customer:return 'list_insurers' if global_listing(text,False) else None
    return None

def global_listing(text,explicit_entity):
    if explicit_entity:return False
    if re.search(r'\b(my|his|her|its|their|he|she|him|il|elle|lui|mes|mon|ses|son|sa|mte3i|mte3ou|mta3ou|mte3ha|hedha|hedhi|first|premier|premiere|louleni)\b',text):return False
    if re.search(r'\b(all|tous|toutes|tout|lkol|elkol|kol)\b',text):return True
    if re.search(r'\b(of|for|by|de|du|par|chez|mta|mta3|mte3|3and)\s+\w+',text):return False
    return bool(re.search(r'\b(customers|clients|assures|users|insurers|companies|compagnies|assureurs|contracts|policies|contrats|polices|assets|property|biens|proprietes|directory|repertoire|disponibles|enregistres|registered|database|base)\s*[?.!]*$',text))
