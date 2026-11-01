"""Registre de toutes les entités gérées par le moteur CRUD.

Un nouveau module = un fichier dans services/ + une ligne ici.
"""
from . import acteurs, garanties, indemnisation, sinistres

REGISTRE = {e.slug: e for module in (sinistres, indemnisation, garanties, acteurs) for e in module.ENTITES}
