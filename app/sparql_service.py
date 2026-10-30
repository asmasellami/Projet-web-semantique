from urllib.parse import urlencode
from urllib.request import Request, urlopen

from SPARQLWrapper import SPARQLWrapper, JSON

FUSEKI = "http://localhost:3030/assurance"

PREFIX = (
    "PREFIX : <http://www.esprit.tn/ontologies/assurance-sinistres#>\n"
    "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
    "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
)

def query(q):
    s = SPARQLWrapper(f"{FUSEKI}/query")
    s.setQuery(PREFIX + q)
    s.setReturnFormat(JSON)
    return s.query().convert()["results"]["bindings"]

def update(q):
    """Exécute une requête SPARQL Update (INSERT / DELETE) sur Fuseki."""
    data = urlencode({"update": PREFIX + q}).encode()
    with urlopen(Request(f"{FUSEKI}/update", data=data), timeout=15):
        pass

if __name__ == "__main__":
    for r in query("SELECT ?num WHERE { ?s :numeroDossier ?num . }"):
        print(r["num"]["value"])
