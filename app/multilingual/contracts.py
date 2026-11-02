from dataclasses import dataclass

@dataclass(frozen=True)
class Contract:
    label: str
    title: str
    entity_type: str
    path: str
    example: str

CONTRACTS = {
    c.label: c for c in [
        Contract('biens_assure', 'Biens assurés', 'Assure', 'Assuré → propriété / contrat → bien', 'warini les biens mta3 Ahmed'),
        Contract('assures_compagnie', "Clients d’une compagnie", 'CompagnieAssurance', 'Compagnie → contrat → assuré', 'Who is insured by MedAssur?'),
        Contract('contrats_assure', "Contrats d’un assuré", 'Assure', 'Assuré → contrat', 'Show policies held by Ahmed'),
        Contract('sinistres_filtres', 'Recherche de sinistres', '', 'Sinistre → lieu / statut / date / type', 'warini les sinistres fi Tunis'),
        Contract('garanties_contrat', 'Garanties du contrat', 'ContratAssurance', 'Contrat → garantie', 'Which guarantees are in AUTO-2026-001?'),
        Contract('clauses_contrat', 'Clauses du contrat', 'ContratAssurance', 'Contrat → clause', 'Les clauses du contrat AUTO-2026-001'),
        Contract('dommages_sinistre', 'Dommages du sinistre', 'Sinistre', 'Sinistre → dommage', 'chniya les degats mta3 S001'),
        Contract('expertises_sinistre', 'Expertises du sinistre', 'Sinistre', 'Sinistre → expertise → expert', 'Who assessed claim S001?'),
        Contract('indemnisation_sinistre', 'Indemnisation du sinistre', 'Sinistre', 'Sinistre → indemnisation → montant', '9adech tkhalles pour S001'),
        Contract('baremes_sinistre', 'Barèmes applicables', 'Sinistre', 'Sinistre → garantie → barème', 'Quel barème pour S001 ?'),
    ]
}

for c in [
    Contract('list_customers','Clients','', 'Graphe → assurés', 'Show all customers'),
    Contract('list_insurers','Compagnies d’assurance','', 'Graphe → compagnies', 'Liste les compagnies assurance'),
    Contract('list_policies','Contrats','', 'Graphe → contrats', 'warini les contrats lkol'),
    Contract('list_assets','Biens assurés','', 'Graphe → biens', 'Show all insured assets'),
    Contract('owner_vehicle','Propriétaire du véhicule','BienAssure','Véhicule → propriétaire','who owns car 123 TU 4567'),
    Contract('policies_vehicle','Contrats couvrant ce bien','BienAssure','Bien ← contrat','Which policies cover car 123 TU 4567?'),
    Contract('issuer_policy','Compagnie du contrat','ContratAssurance','Contrat → compagnie','Who issued policy AUTO-2026-001?'),
    Contract('holder_policy','Souscripteur du contrat','ContratAssurance','Contrat → assuré','Who holds policy AUTO-2026-001?'),
    Contract('claim_details','Fiche du sinistre','Sinistre','Sinistre → fiche','Show claim S001'),
    Contract('customer_claims','Sinistres du client','Assure','Assuré ← contrat ← sinistre','Show claims for Ahmed'),
    Contract('policy_assets','Biens couverts par le contrat','ContratAssurance','Contrat → bien','Show assets covered by AUTO-2026-001'),
    Contract('policy_claims','Sinistres du contrat','ContratAssurance','Contrat ← sinistre','Show claims of AUTO-2026-001'),
    Contract('insurer_policies','Contrats de la compagnie','CompagnieAssurance','Compagnie → contrats','Show policies issued by MedAssur'),
]:
    CONTRACTS[c.label]=c

RESULT_TYPES={
    'list_customers':'Assure','assures_compagnie':'Assure','owner_vehicle':'Assure','holder_policy':'Assure',
    'list_insurers':'CompagnieAssurance','issuer_policy':'CompagnieAssurance',
    'list_policies':'ContratAssurance','contrats_assure':'ContratAssurance','policies_vehicle':'ContratAssurance',
    'list_assets':'BienAssure','biens_assure':'BienAssure','list_claims':'Sinistre',
    'claim_details':'Sinistre','customer_claims':'Sinistre','sinistres_filtres':'Sinistre',
    'policy_assets':'BienAssure','policy_claims':'Sinistre','insurer_policies':'ContratAssurance',
}
