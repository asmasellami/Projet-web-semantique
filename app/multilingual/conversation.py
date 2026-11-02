"""Bounded, typed conversation state. No user-supplied graph identifier is trusted."""
import re
from dataclasses import asdict
from .contracts import CONTRACTS
from .engine import Answer,answer,catalogue,matching_groups,alias_matches
from .classifier import predict
from .routing import route
from .text import normalize

SESSION_KEY='insurance_chat_v2'
FOCUS_TYPES={'Assure','ContratAssurance','BienAssure','Sinistre','CompagnieAssurance'}
KIND_NAMES={'Assure':'Client','ContratAssurance':'Contrat','BienAssure':'Bien assuré','Sinistre':'Sinistre','CompagnieAssurance':'Compagnie'}
MAX_TURNS=12

def initial_state():return {'focus':None,'history':[],'last_rows':[],'pending':None,'version':0,'last_question':''}

def verified_focus(kind,ids):
    if kind not in FOCUS_TYPES:return None
    selected=set(ids)
    return next(({'kind':kind,'kind_name':KIND_NAMES[kind],'ids':sorted(g['ids']),'name':g['name']} for g in catalogue(kind) if selected and selected<=set(g['ids'])),None)

def desired_kind(question):
    text=normalize(question)
    def has(kind):return bool(matching_groups(text,catalogue(kind)))
    label=route(text,has)
    if not label:
        p=predict(text);label=p['label'] if p['accepted'] else ''
    return CONTRACTS[label].entity_type if label in CONTRACTS else ''

def contextual_question(question,state):
    text=normalize(question)
    contextual=bool(re.search(r'\b(his|her|it|its|their|he|she|him|this|that|these|those|il|elle|lui|houwa|ses|son|sa|ce|cet|cette|ces|mte3ou|mta3ou|mte3ha|mta3ha|hedhi|hedha|first|premier|premiere|louleni)\b',text))
    contextual=contextual or bool(re.match(r'^(and|et|w)\b',text))
    if not contextual:return question,None
    # Learn the requested entity type from relation words before injecting context.
    kind=desired_kind(question)
    focus=state.get('focus')
    if re.search(r'\b(claims|sinistres)\b',text):
        kind=focus['kind'] if focus and focus['kind'] in {'Assure','ContratAssurance','Sinistre'} else 'Assure'
    elif focus and focus['kind']=='ContratAssurance' and re.search(r'\b(assets|biens|properties)\b',text):kind='ContratAssurance'
    elif focus and focus['kind']=='CompagnieAssurance' and re.search(r'\b(policies|contracts|contrats|polices)\b',text):kind='CompagnieAssurance'
    if not kind:return question,None
    if any(matching_groups(text,catalogue(k)) for k in FOCUS_TYPES):return question,None
    unknown=re.search(r'\b(?:of|for|de|du|par|mta3|mte3)\s+([a-z][\w-]*)',text)
    if unknown and unknown[1] not in {'him','her','it','them','lui','elle','ses','son','sa','this','that','the','ce','cet','cette','ces','hedha','hedhi','first','premier','premiere','louleni'}:
        return Answer(question,message='Ce nom est inconnu. Précisez une personne ou un identifiant connu.'),None
    if re.search(r'\b(first|premier|premiere|louleni)\b',text):
        rows=[r for r in state.get('last_rows',[]) if r.get('kind')==kind]
        focus=verified_focus(kind,rows[0].get('ids',[rows[0]['item']])) if rows else None
    elif focus and focus['kind']==kind:
        focus=verified_focus(kind,focus['ids'])
    else:focus=None
    if focus:
        # IDs come from the graph. The original question stays visible in history.
        return question+' '+focus['ids'][0],focus
    rows=[r for r in state.get('last_rows',[]) if r.get('kind')==kind]
    candidates=[]
    for row in rows:
        verified=verified_focus(kind,row.get('ids',[row['item']]))
        if verified and verified not in candidates:candidates.append(verified)
    rep=Answer(question,status='ambiguous' if candidates else 'clarify',message='Sélectionnez la personne ou le dossier concerné avant cette question.')
    rep.candidates=[{'name':c['name'],'ids':','.join(c['ids'])} for c in candidates]
    return rep,{'kind':kind,'question':question,'contextual':True} if candidates else None

def add_turn(state,question,rep):
    # Bound both transcript and rows stored in the server-side session.
    rep.rows=rep.rows[:50]
    state['history']=(state.get('history',[])+[{'question':question,'reply':asdict(rep)}])[-MAX_TURNS:]
    state['version']=state.get('version',0)+1
    return rep

def submit(question,state):
    state['pending']=None
    if state.get('focus'):
        state['focus']=verified_focus(state['focus']['kind'],state['focus']['ids'])
    text=normalize(question)
    # A bare known name/ID is a natural explicit selection, not a guessed query.
    selection=re.sub(r'^(select|choose|selectionne|choisis|choisir|ikhtar|e5tar|n5tar)\s+(?:(?:customer|client|policy|contrat|vehicle|vehicule)\s+)?','',text)
    if len(selection.split())<=5:
        candidates=[]
        for kind in FOCUS_TYPES:
            for group in catalogue(kind):
                if any(normalize(a)==selection or (re.fullmatch(r'\d{1,4}\s*tu\s*\d{1,4}',selection) and alias_matches(selection,a)) for a in group['aliases'] if a):
                    candidates.append(verified_focus(kind,group['ids']))
        if len(candidates)==1:
            state['focus']=candidates[0];state['last_rows']=[];state['last_question']=''
            return add_turn(state,question,Answer(question,status='selected',message='Sélection : '+candidates[0]['name']))
        if len(candidates)>1 and len({c['kind'] for c in candidates})==1:
            rep=Answer(question,status='ambiguous',message='Plusieurs personnes correspondent : choisissez un résultat.')
            rep.candidates=[{'name':c['name'],'ids':','.join(c['ids'])} for c in candidates]
            state['pending']={'kind':candidates[0]['kind'],'question':question,'selection_only':True}
            return add_turn(state,question,rep)
        if selection!=text:
            return add_turn(state,question,Answer(question,message='Ce nom ou identifiant est inconnu. Choisissez un résultat de la liste.'))
    effective,context=contextual_question(question,state)
    if isinstance(effective,Answer):
        state['pending']=context
        return add_turn(state,question,effective)
    if re.match(r'^(only|seulement|ken)\b',text):
        if not state.get('last_question'):
            return add_turn(state,question,Answer(question,message='Commencez par rechercher des sinistres ou sélectionner un dossier.'))
        effective=state['last_question']+' '+question
    rep=answer(effective)
    rep.question=question
    if rep.status=='ambiguous':
        kind=CONTRACTS[rep.intent].entity_type
        state['pending']={'kind':kind,'question':effective,'contextual':False}
    if rep.status in ['ok','empty']:
        state['last_rows']=rep.rows[:50];state['last_question']=effective
        if rep.entities:
            kind=CONTRACTS[rep.intent].entity_type
            state['focus']=verified_focus(kind,rep.entities)
        elif rep.intent.startswith('list_') or rep.intent=='sinistres_filtres':
            state['focus']=None
    return add_turn(state,question,rep)

def select(item,state):
    pending=state.get('pending')
    last=state.get('history',[])[-1]['reply'] if state.get('history') else {}
    if pending:
        allowed={c['ids'] for c in last.get('candidates',[])}
        if item not in allowed:raise ValueError('Cette sélection a expiré. Choisissez parmi les derniers résultats.')
        focus=verified_focus(pending['kind'],item.split(','))
    else:
        row=next((r for r in state.get('last_rows',[]) if r['item']==item),None)
        focus=verified_focus(row['kind'],row.get('ids',[item])) if row and row.get('kind') in FOCUS_TYPES else None
    if not focus:raise ValueError('Cet élément est introuvable ou ne peut pas être sélectionné.')
    state['focus']=focus;state['pending']=None
    if pending and not pending.get('selection_only'):
        question=pending['question']
        if pending['contextual']:
            return submit(question,state)
        rep=answer(question,','.join(focus['ids']))
        if rep.status in ['ok','empty']:
            state['last_rows']=rep.rows[:50];state['last_question']=question
        return add_turn(state,'Sélection : '+focus['name'],rep)
    state['last_rows']=[];state['last_question']=''
    return add_turn(state,'Sélection : '+focus['name'],Answer('',status='selected',message='Que souhaitez-vous consulter pour '+focus['name']+' ?'))

def suggestions(state):
    focus=state.get('focus')
    initial=[('Explorer les clients','Show all customers'),('Explorer les compagnies','List all insurance companies'),('Explorer les contrats','Show all policies'),('Explorer les biens','Show all insured assets')]
    history=state.get('history',[])
    last=history[-1]['reply'] if history else {}
    if last.get('status')=='clarify' and 'Par « assurances »' in last.get('message',''):
        return [{'label':label,'question':q} for label,q in initial[1:3]]
    selections=[]
    if state.get('pending'):
        selections=[{'label':'Choisir '+c['name'],'action':'select','item':c['ids']} for c in last.get('candidates',[])[:4]]
    else:
        for row in state.get('last_rows',[]):
            if row.get('kind') in FOCUS_TYPES and (not focus or set(row.get('ids',[row['item']]))!=set(focus['ids'])):
                selections.append({'label':'Choisir '+(row.get('name') or row['item']),'action':'select','item':row['item']})
                if len(selections)==3:break
    if not focus:return selections+[{'label':label,'question':q} for label,q in initial]
    ref=focus['ids'][0]
    choices={
        'Assure':[('Ses contrats','Show policies held by '+ref),('Ses biens assurés','Show insured assets of '+ref),('Ses sinistres','Show claims for '+ref)],
        'ContratAssurance':[('Ses garanties','Show guarantees of '+ref),('Ses clauses','Show clauses of '+ref),('Biens couverts','Show assets covered by '+ref),('Souscripteur','Who holds policy '+ref),('Compagnie','Who issued policy '+ref),('Sinistres liés','Show claims of '+ref)],
        'BienAssure':[('Son propriétaire','Who owns vehicle '+ref),('Contrats couvrants','Which policies cover vehicle '+ref)],
        'CompagnieAssurance':[('Ses clients','Show customers of '+ref),('Ses contrats','Show policies issued by '+ref)],
        'Sinistre':[('Sa fiche','Show claim '+ref),('Dommages','Show damage for '+ref),('Expertises','Show assessments for '+ref),('Indemnisation','Show payments for '+ref),('Barèmes','Show scales for '+ref)],
    }
    return selections+[{'label':label,'question':q} for label,q in choices[focus['kind']]]+[{'label':'Explorer d’autres clients','question':'Show all customers'}]
