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
