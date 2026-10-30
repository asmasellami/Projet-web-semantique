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


def remplacer(sujet, props):
    """Remplace toutes les valeurs des propriétés données (None = simple suppression)."""
    ops = []
    for p, v in props.items():
        ops.append(f"DELETE WHERE {{ :{sujet} :{p} ?o }}")
        for x in _valeurs(v):
            if x is not None:
                ops.append(f"INSERT DATA {{ :{sujet} :{p} {x} }}")
    update(" ;\n".join(ops))


def supprimer(sujet):
    """Supprime l'individu et toutes les références vers lui."""
    update(f"DELETE WHERE {{ :{sujet} ?p ?o }} ;\nDELETE WHERE {{ ?s ?p :{sujet} }}")
