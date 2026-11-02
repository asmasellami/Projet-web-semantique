import calendar
import re
import time
from dataclasses import dataclass, field
from datetime import date
from app import sparql_service
from .classifier import predict
from .contracts import CONTRACTS
from .queries import build
from .text import normalize, word_present

@dataclass
class Answer:
    question: str
    status: str = 'clarify'
    message: str = ''
    intent: str = ''
    title: str = ''
    path: str = ''
    prediction: dict = field(default_factory=dict)
    entities: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    filters: dict = field(default_factory=dict)
    query: str = ''
    rows: list = field(default_factory=list)
    milliseconds: float = 0

def catalogue(kind):
    rows = sparql_service.query(f'''SELECT ?s ?name ?cin ?ref WHERE {{
      ?s a :{kind} . OPTIONAL {{ ?s :nom ?name }} OPTIONAL {{ ?s :cin ?cin }}
      OPTIONAL {{ ?s ?p ?ref . VALUES ?p {{ :numeroContrat :numeroDossier }} }} }}''')
    groups = {}
    for row in rows:
        identifier = row['s']['value'].split('#')[-1]
        if not re.fullmatch(r'[A-Za-z0-9_]+', identifier):
            continue
        name = row.get('name',{}).get('value','')
        cin = row.get('cin',{}).get('value','')
        key = (normalize(name),cin) if name and cin else (identifier,)
        g = groups.setdefault(key, {'ids':[], 'name':name or identifier, 'aliases':set()})
        if identifier not in g['ids']:
            g['ids'].append(identifier)
        g['aliases'].update([identifier, identifier.replace('_',' '),name, row.get('ref',{}).get('value','')])
        if kind=='Sinistre':
            g['aliases'].add(identifier.rsplit('_',1)[-1])
        if kind=='Assure' and name:
            g['aliases'].add(name.split()[0])
    return list(groups.values())

STATUS = {'Déclaré':['declared','declare','declares','tsarra7','declaree'], 'En expertise':['en expertise','under assessment','under review','expertise en cours'], 'Indemnisé':['indemnise','indemnises','compensated','paid','tkhalles'], 'Refusé':['refuse','rejected','refused','marfoudh'], 'Clôturé':['cloture','closed','msakker']}
TYPES = {'Accident':['accident','accidents'], 'Incendie':['incendie','incendies','fire','fires','7ri9'], 'Vol':['vol','theft','stolen','ser9a'], 'DegatDesEaux':['degats des eaux','water damage'], 'CatastropheNaturelle':['catastrophe naturelle','natural disaster']}
MONTHS = ['janvier january janvier','fevrier february fevri','mars march','avril april','mai may','juin june','juillet july','aout august','septembre september','octobre october octobre','novembre november','decembre december']

def extract_filters(text, label):
    f = {}
    if label=='biens_assure':
        owned = any(word_present(text,x) for x in ['own','owns','owned','belonging','possede','possedes','appartiennent','appartenant','proprietaire','yomlek','milk'])
        covered = any(word_present(text,x) for x in ['covered','couverts','couvre','couvert','coverage','assures','insured','assures'])
        f['relationship'] = 'owned' if owned else 'covered' if covered else 'associated'
        if any(word_present(text,x) for x in ['vehicule','vehicle','voiture','car','vehicules','vehicles','voitures','cars']):
            f['subtype']='Vehicule'
        elif any(word_present(text,x) for x in ['home','logement','maison','house','homes','logements','dyar']):
            f['subtype']='Logement'
    if label=='clauses_contrat':
        if any(word_present(text,x) for x in ['exclusions','exclusion']):
            f['subtype']='ClauseExclusion'
        elif any(word_present(text,x) for x in ['deductible','deductibles','franchise','franchises']) and not word_present(text,'clauses'):
            f['subtype']='ClauseFranchise'
    if label=='garanties_contrat':
        coverage={'GarantieIncendie':['fire','incendie','7ri9'], 'GarantieVol':['theft','vol','ser9a'], 'GarantieResponsabiliteCivile':['liability','responsabilite civile'], 'GarantieBrisDeGlace':['glass','bris de glace'], 'GarantieHospitalisation':['hospitalisation','hospitalization'], 'GarantieDegatsDesEaux':['water damage','degats des eaux']}
        matched=[kind for kind,aliases in coverage.items() if any(word_present(text,a) for a in aliases)]
        if len(matched)>1:
            raise ValueError('Précisez un seul type de garantie.')
        if matched:
            f['subtype']=matched[0]
    if label=='sinistres_filtres':
        locations = sparql_service.query('SELECT DISTINCT ?l WHERE { ?s :lieuSinistre ?l }')
        aliases=set(r['l']['value'].split(',')[0].strip() for r in locations)
        matched = [loc for loc in aliases if word_present(text,loc)]
        if len(matched)>1:
            raise ValueError('Précisez un seul lieu / Please specify one location.')
        if matched:
            f['location'] = matched[0]
        else:
            place = re.search(r'\b(?:fi|in|a|at)\s+([a-z][a-z -]*?)(?:\s+(?:before|after|avant|apres|en|in|between|entre)\b|[?.!]|$)',text)
            if place and not any(word_present(place[1],m) for months in MONTHS for m in months.split()) and place[1] not in ['expertise']:
                f['location'] = place[1].strip()
        for key, mapping in [('status',STATUS),('type',TYPES)]:
            matches = [canonical for canonical,aliases in mapping.items() if any(word_present(text,a) for a in aliases)]
            if len(matches)>1:
                raise ValueError('Plusieurs valeurs détectées : précisez un statut/type unique.')
            if matches:
                f[key]=matches[0]
        dates = re.findall(r'\b\d{4}-\d{2}-\d{2}\b',text)
        if len(dates)>2:
            raise ValueError('Précisez une date ou un intervalle de deux dates.')
        if len(dates)==2:
            f.update(date_from=date.fromisoformat(dates[0]).isoformat(),date_to=date.fromisoformat(dates[1]).isoformat())
        elif dates:
            dt=date.fromisoformat(dates[0]).isoformat()
            if re.search(r'\b(before|avant|9bal)\b',text):
                f['date_to']=(date.fromisoformat(dt)-__import__('datetime').timedelta(days=1)).isoformat()
            elif re.search(r'\b(after|apres|ba3d)\b',text):
                f['date_from']=(date.fromisoformat(dt)+__import__('datetime').timedelta(days=1)).isoformat()
            else:
                f.update(date_from=dt,date_to=dt)
        else:
            for month,words in enumerate(MONTHS,1):
                if any(word_present(text,w) for w in words.split()):
                    year=re.search(r'\b(20\d{2})\b',text)
                    if not year:
                        raise ValueError('Quelle année ? / Which year? / anehou 3am?')
                    y=int(year[1]); f.update(date_from=f'{y}-{month:02}-01',date_to=f'{y}-{month:02}-{calendar.monthrange(y,month)[1]}')
            if not f.get('date_from'):
                years=re.findall(r'\b20\d{2}\b',text)
                if len(years)>1:
                    raise ValueError('Utilisez deux dates explicites pour un intervalle.')
                if years:
                    f.update(date_from=years[0]+'-01-01',date_to=years[0]+'-12-31')
            if re.search(r'\b(before|after|avant|apres|9bal|ba3d|since|depuis|between|entre)\b',text):
                raise ValueError('Utilisez des dates explicites AAAA-MM-JJ pour cette comparaison.')
        if f.get('date_from','')>f.get('date_to','9999'):
            raise ValueError('Intervalle de dates inversé / Reversed date range.')
    amount=re.search(r'(above|over|more than|superieur a|plus de|fou9|below|under|less than|inferieur a|moins de|a9al men)\s+(\d+(?:[.,]\d+)?)',text)
    if amount:
        if label!='indemnisation_sinistre':
            raise ValueError('Le filtre montant est disponible pour les indemnisations uniquement.')
        f['amount']=['>' if amount[1] in ['above','over','more than','superieur a','plus de','fou9'] else '<',amount[2].replace(',','.')]
    elif re.search(r'\b(above|below|more than|less than|superieur a|inferieur a|plus de|moins de|fou9|a9al men)\b',text):
        raise ValueError('Précisez un montant numérique positif ou nul.')
    if re.search(r'\b(?:\d{1,2}/\d{1,2}/\d{2,4}|last month|last year|mois dernier|semaine derniere|chhar li fet)\b',text):
        raise ValueError('Utilisez une date explicite AAAA-MM-JJ ou un mois avec année.')
    if label!='sinistres_filtres' and (re.search(r'\b\d{4}-\d{2}-\d{2}\b',text) or re.search(r'\b(active|actif|expired|expire|suspended|suspendu)\b',text)):
        raise ValueError('Les filtres date/statut sont disponibles pour les sinistres uniquement dans cette version.')
    return f

def answer(question, selected=''):
    started=time.perf_counter(); r=Answer(question or '')
    try:
        if not isinstance(question,str) or not question.strip() or len(question)>300:
            raise ValueError('Saisissez une question de 1 à 300 caractères.')
        text=normalize(question)
        if any(x in text for x in ['{','}',';','\\','<','>','`']) or re.search(r'\b(insert|delete|drop|clear|load|service)\b',text):
            r.status='rejected'; r.message='Question refusée : lecture seule, sans code SPARQL.'; return r
        if re.search(r'\b(how many|combien de|nombre de|supprime|delete|remove|create|ajoute|compare|fassa5|baddel|update|cancel|annule|annulili)\b',text) or re.match(r'^(does|is there|est ce que|famma)\b',text):
            r.status='unsupported'; r.message='Cette opération n’est pas prise en charge. Demandez une liste.'; return r
        if re.search(r'\b(not|without|sans|sauf|except|excluding|pas)\b',text):
            r.status='unsupported'; r.message='Les exclusions/négations dans les questions ne sont pas encore prises en charge.'; return r
        r.prediction=predict(text)
        label=r.prediction['label']
        if not r.prediction['accepted'] or label not in CONTRACTS:
            r.status='unsupported'; r.message='Question non reconnue avec assez de confiance. Reformulez avec les exemples.'; return r
        if label!='indemnisation_sinistre' and re.search(r'\b(9adech|9addesh)\b',text):
            r.status='unsupported'; r.message='Le comptage n’est pas encore disponible.'; return r
        c=CONTRACTS[label]; r.intent=label; r.title=c.title; r.path=c.path
        r.filters=extract_filters(text,label)
        if c.entity_type:
            groups=catalogue(c.entity_type)
            # Longest matching alias wins; all equal-specificity matches remain ambiguous.
            scored=[(max([len(normalize(a)) for a in g['aliases'] if a and word_present(text,a)] or [0]),g) for g in groups]
            best=max([score for score,g in scored] or [0])
            matches=[g for score,g in scored if score==best and score>0]
            if selected:
                selected_ids=set(selected.split(','))
                matches=[g for g in matches if selected_ids==set(g['ids'])]
            if not matches:
                r.message=f'Précisez un identifiant ou nom connu ({c.entity_type}). / Specify a known name or ID.'
                return r
            # Two distinct explicit entity aliases are never silently reduced to one request.
            all_matches=[g for score,g in scored if score>0]
            if len(all_matches)>1 and len(matches)==1 and not selected:
                matches=all_matches
            if len(matches)>1:
                r.status='ambiguous'; r.message='Plusieurs entités correspondent : choisissez une seule.'
                r.candidates=[{'name':g['name'],'ids':','.join(g['ids'])} for g in matches]; return r
            r.entities=matches[0]['ids']
        elif not r.filters:
            # Listing all claims is supported; an unrecognised filter must not be ignored.
            if re.search(r'\b(before|after|avant|apres|between|entre|above|below|since|depuis)\b',text):
                raise ValueError('Précisez le filtre demandé avec une valeur explicite.')
        q=build(label,r.entities,r.filters)
        r.query=sparql_service.PREFIX+q
        bindings=sparql_service.query(q)
        columns=['item','name','detail','amount','location','status','date']
        for b in bindings:
            r.rows.append({k:(b.get(k,{}).get('value','').split('#')[-1] if k=='item' else b.get(k,{}).get('value','')) for k in columns})
        r.status='ok' if r.rows else 'empty'
        r.message='Question comprise / Understood / fhemt sou2alek' if r.rows else 'Aucun résultat / No matching records / ma famech resultat'
    except ValueError as err:
        r.status='clarify'; r.message=str(err)
    except (ImportError,FileNotFoundError) as err:
        r.status='model_unavailable'; r.message='Modèle local indisponible. Voir README (entraînement / installation).'
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Multilingual query failed')
        r.status='error'; r.message='Service indisponible. Vérifiez Fuseki et le modèle local.'
    finally:
        r.milliseconds=round((time.perf_counter()-started)*1000,1)
    return r
