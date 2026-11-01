"""Outils communs : littéraux SPARQL sûrs et opérations CRUD génériques sur un individu."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from django.http import Http404

from app.sparql_service import query, update


# ---------- Identifiants et libellés ----------
def local(uri):
    return uri.split("#")[-1]


def libelle(uri):
    return local(uri).replace("_", " ")


def identifiant_valide(ident):
    """Protège les requêtes : un id d'URL ne contient que lettres, chiffres et _."""
    if not re.fullmatch(r"[A-Za-z0-9_]+", ident):
        raise Http404("Identifiant invalide")
    return ident


def fabriquer_id(prefixe, texte):
    nettoye = re.sub(r"[^A-Za-z0-9]+", "_", texte.strip()).strip("_")
    return f"{prefixe}_{nettoye}"


# ---------- Littéraux SPARQL (toujours échappés / validés) ----------
def chaine(v):
    v = v.strip().replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ").replace("\r", " ")
    return f'"{v}"'


def entier(v):
    try:
        return f'"{int(v)}"^^xsd:integer'
    except ValueError:
        raise ValueError("Un nombre entier est attendu.")


def decimal(v):
    try:
        return f'"{Decimal(v.strip().replace(",", "."))}"^^xsd:decimal'
    except InvalidOperation:
        raise ValueError("Un nombre est attendu.")


def date_heure(v):
    try:
        return f'"{date.fromisoformat(v.strip()).isoformat()}T00:00:00"^^xsd:dateTime'
    except ValueError:
        raise ValueError("Date invalide (format AAAA-MM-JJ).")


def booleen(b):
    return f'"{"true" if b else "false"}"^^xsd:boolean'


def texte_filtre(v):
    """Valeur de recherche utilisée dans un FILTER : guillemets et antislash retirés."""
    return v.replace('"', "").replace("\\", "").strip()


# ---------- Opérations CRUD ----------
def existe(sujet):
    return bool(query(f"SELECT ?t WHERE {{ :{sujet} a ?t }} LIMIT 1"))


def lister_individus(classe):
    """Individus d'une classe, sous forme [(id, libellé)]."""
    rows = query(f"SELECT DISTINCT ?i WHERE {{ ?i a :{classe} }} ORDER BY ?i")
    return [(local(r["i"]["value"]), libelle(r["i"]["value"])) for r in rows]


def _valeurs(v):
    return v if isinstance(v, list) else [v]


def creer(sujet, classes, props):
    """props : {propriété: littéral SPARQL | liste de littéraux | None}."""
    lignes = [f":{sujet} a owl:NamedIndividual"] + [f":{sujet} a :{c}" for c in classes]
    for p, v in props.items():
        if v is not None:
            lignes += [f":{sujet} :{p} {x}" for x in _valeurs(v)]
    update("INSERT DATA {\n" + " .\n".join(lignes) + " .\n}")


def _termes(b):
    """Écritures SPARQL possibles d'une valeur renvoyée par Fuseki.

    Jena ne retrouve pas toujours un décimal stocké (« 500 ») avec un motif à variable
    (`DELETE WHERE { ?s ?p ?o }`) : on supprime donc avec DELETE DATA, en essayant
    plusieurs écritures du même nombre.
    """
    if b["type"] == "uri":
        return [f"<{b['value']}>"]
    if b["type"] != "literal":
        return []
    valeurs = [b["value"]]
    dt = b.get("datatype", "")
    if dt.endswith("#decimal"):
        try:
            d = Decimal(b["value"])
            valeurs += [format(d.normalize(), "f"), format(d, "f"), f"{d:.1f}"]
        except InvalidOperation:
            pass
    termes = []
    for v in dict.fromkeys(valeurs):
        lex = (v.replace("\\", "\\\\").replace('"', '\\"')
                .replace("\n", "\\n").replace("\r", "\\r"))
        if "xml:lang" in b:
            termes.append(f'"{lex}"@{b["xml:lang"]}')
        elif dt:
            termes.append(f'"{lex}"^^<{dt}>')
        else:
            termes.append(f'"{lex}"')
    return termes


def _effacer(sujet, props=None):
    """Supprime les valeurs de `sujet` (toutes, ou celles des propriétés données)."""
    filtre = ""
    if props:
        filtre = "VALUES ?p { " + " ".join(f":{p}" for p in props) + " }"
    triples = []
    for r in query(f"SELECT ?p ?o WHERE {{ :{sujet} ?p ?o . {filtre} }}"):
        for terme in _termes(r["o"]):
            triples.append(f":{sujet} <{r['p']['value']}> {terme} .")
    if triples:
        update("DELETE DATA {\n" + "\n".join(triples) + "\n}")


def remplacer(sujet, props):
    """Remplace toutes les valeurs des propriétés données (None = simple suppression)."""
    _effacer(sujet, list(props))
    ops = []
    for p, v in props.items():
        for x in _valeurs(v):
            if x is not None:
                ops.append(f"INSERT DATA {{ :{sujet} :{p} {x} }}")
    if ops:
        update(" ;\n".join(ops))


def supprimer(sujet):
    """Supprime l'individu et toutes les références vers lui."""
    _effacer(sujet)
    update(f"DELETE WHERE {{ ?s ?p :{sujet} }}")
