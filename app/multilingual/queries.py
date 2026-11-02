"""Only known identifiers, typed values and fixed predicates reach these templates."""
import re
from datetime import date
from app.services.rdf import chaine

def values(ids):
    if not ids or any(not re.fullmatch(r'[A-Za-z0-9_]+', x) for x in ids):
        raise ValueError('Invalid graph identifier')
    return 'VALUES ?entity { ' + ' '.join(':'+x for x in ids) + ' }'

def build(label, ids, filters):
    v = values(ids) if ids else ''
    if label in ('list_customers','list_insurers','list_policies','list_assets'):
        cls={'list_customers':'Assure','list_insurers':'CompagnieAssurance','list_policies':'ContratAssurance','list_assets':'BienAssure'}[label]
        body=f'?item a :{cls} . OPTIONAL {{ ?item :numeroContrat ?ref }} OPTIONAL {{ ?item :immatriculation ?plate }} OPTIONAL {{ ?item :cin ?cin }} BIND(COALESCE(?ref,?plate,?cin,"") AS ?detail)'
    elif label == 'owner_vehicle':
        body='{ ?entity :appartientA ?item } UNION { ?item :estProprietaireDe ?entity }'
    elif label == 'policies_vehicle':
        body='?item :couvreBien ?entity . OPTIONAL { ?item :numeroContrat ?detail }'
    elif label == 'issuer_policy':
        body='{ ?entity :estEmisPar ?item } UNION { ?item :emet ?entity }'
    elif label == 'holder_policy':
        body='{ ?entity :estSouscritPar ?item } UNION { ?item :souscrit ?entity }'
    elif label == 'policy_assets':
        body='?entity :couvreBien ?item . OPTIONAL { ?item :immatriculation ?detail }'
    elif label == 'insurer_policies':
        body='{ ?entity :emet ?item } UNION { ?item :estEmisPar ?entity }'
    elif label in ('claim_details','customer_claims','policy_claims'):
        body='?entity a :Sinistre . BIND(?entity AS ?item)' if label=='claim_details' else '{ ?entity :estConcerneParSinistre ?item } UNION { ?item :concerneContrat ?entity }' if label=='policy_claims' else '{ ?p :estSouscritPar ?entity ; :estConcerneParSinistre ?item } UNION { ?item :concerneContrat ?p . ?p :estSouscritPar ?entity }'
        body='{ '+body+' } ?item a :Sinistre . OPTIONAL { ?item :numeroDossier ?detail } OPTIONAL { ?item :lieuSinistre ?location } OPTIONAL { ?item :statutDossier ?status } OPTIONAL { ?item :dateSinistre ?date }'
    elif label == 'biens_assure':
        owned = '{ ?entity :estProprietaireDe ?item } UNION { ?item :appartientA ?entity }'
        covered = '{ ?policy :estSouscritPar ?entity ; :couvreBien ?item } UNION { ?entity :souscrit ?policy . ?policy :couvreBien ?item }'
        mode = filters.get('relationship', 'associated')
        body = owned if mode == 'owned' else covered if mode == 'covered' else owned + ' UNION ' + covered
        body = '{ ' + body + ' } OPTIONAL { ?item :immatriculation ?detail }'
    elif label == 'assures_compagnie':
        body = '{ ?policy :estEmisPar ?entity ; :estSouscritPar ?item } UNION { ?entity :emet ?policy . ?policy :estSouscritPar ?item }'
    elif label == 'contrats_assure':
        body = '{ ?item :estSouscritPar ?entity } UNION { ?entity :souscrit ?item }'
        body = '{ ' + body + ' } OPTIONAL { ?item :numeroContrat ?detail }'
    elif label == 'garanties_contrat':
        body = '?entity :inclutGarantie ?item . OPTIONAL { ?item :codeGarantie ?detail }'
    elif label == 'clauses_contrat':
        body = '?entity :contientClause ?item . OPTIONAL { ?item :texteClause ?detail }'
    elif label == 'dommages_sinistre':
        body = '{ ?entity :causeDommage ?item } UNION { ?item :resulteDe ?entity }'
        body = '{ '+body+' } OPTIONAL { ?item :descriptionDommage ?detail }'
    elif label == 'expertises_sinistre':
        body = '?entity :estEvalueePar ?item . OPTIONAL { ?item :realiseePar ?expert . ?expert :nom ?detail }'
    elif label == 'indemnisation_sinistre':
        body = '{ ?entity :donneLieuA ?item } UNION { ?item :indemniseSinistre ?entity }'
        body = '{ '+body+' } OPTIONAL { ?item :montantVerse ?amount } OPTIONAL { ?item :referencePaiement ?detail }'
    elif label == 'baremes_sinistre':
        body = '{ ?entity :baremeApplicable ?item } UNION { ?entity :concerneContrat/:inclutGarantie/:appliqueBareme ?item } UNION { ?entity :garantieMobilisable/:appliqueBareme ?item }'
        body = '{ '+body+' } OPTIONAL { ?item :referenceBareme ?detail }'
    elif label == 'sinistres_filtres':
        body = '?item a :Sinistre . OPTIONAL { ?item :lieuSinistre ?location } OPTIONAL { ?item :statutDossier ?status } OPTIONAL { ?item :dateSinistre ?date } OPTIONAL { ?item :numeroDossier ?detail }'
        if filters.get('location'):
            body += ' FILTER(CONTAINS(LCASE(STR(?location)), LCASE('+chaine(filters['location'])+')))'
        if filters.get('status'):
            body += ' FILTER(?status = '+chaine(filters['status'])+')'
        if filters.get('type'):
            if filters['type'] not in ('Accident','Incendie','DegatDesEaux','Vol','CatastropheNaturelle'):
                raise ValueError('Invalid claim type')
            body += ' ?item a :'+filters['type']+' .'
        for key, op in [('date_from','>='),('date_to','<=')]:
            if filters.get(key):
                dt = date.fromisoformat(filters[key]).isoformat()
                body += f' FILTER(?date {op} "{dt}T'+('23:59:59' if key=='date_to' else '00:00:00')+'"^^xsd:dateTime)'
    else:
        raise ValueError('Unsupported intention')
    if label in ('customer_claims','claim_details','policy_claims'):
        if filters.get('location'):
            body+=' FILTER(CONTAINS(LCASE(STR(?location)),LCASE('+chaine(filters['location'])+')))'
        if filters.get('status'):
            body+=' FILTER(?status = '+chaine(filters['status'])+')'
        if filters.get('type'):
            if filters['type'] not in ('Accident','Incendie','DegatDesEaux','Vol','CatastropheNaturelle'):raise ValueError('Invalid type')
            body+=' ?item a :'+filters['type']+' .'
        for key,operator in [('date_from','>='),('date_to','<=')]:
            if filters.get(key):
                dt=date.fromisoformat(filters[key]).isoformat()
                body+=f' FILTER(?date {operator} "{dt}T'+('23:59:59' if key=='date_to' else '00:00:00')+'"^^xsd:dateTime)'
    if filters.get('subtype'):
        allowed = {'Vehicule','Logement','ClauseExclusion','ClauseFranchise','GarantieIncendie','GarantieVol','GarantieResponsabiliteCivile','GarantieBrisDeGlace','GarantieHospitalisation','GarantieDegatsDesEaux'}
        if filters['subtype'] not in allowed:
            raise ValueError('Invalid subtype')
        body += ' ?item a :'+filters['subtype']+' .'
    if label == 'indemnisation_sinistre' and filters.get('amount'):
        op, number = filters['amount']
        if op not in ('>', '<', '>=', '<=') or not re.fullmatch(r'\d+(?:\.\d+)?', number):
            raise ValueError('Invalid amount')
        body += f' FILTER(?amount {op} {number})'
    return 'SELECT DISTINCT ?item ?name ?detail ?amount ?location ?status ?date WHERE { '+v+' { '+body+' } OPTIONAL { ?item :nom ?name } } ORDER BY ?item'
