import re
import unicodedata

def normalize(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
    text = re.sub(r'\b(?:mt3ou|mta3o|mte3o|mt3o)\b', 'mte3ou', text)
    text = re.sub(r'\b(?:mt3ha|mta3ha)\b', 'mte3ha', text)
    return re.sub(r'\s+', ' ', text.replace('’', "'")).strip()

def classifier_text(text):
    """Names/numeric identifiers are slots, not intent features. No numeral transliteration."""
    text = normalize(text)
    # Keep the entity TYPE while masking the specific ID. A policy and a claim
    # must not become indistinguishable when learning reverse relationships.
    text = re.sub(r'\b(?:auto|hab|sante)-\d{4}-\d+\b|\bcontrat_[a-z0-9_]+\b',' policy_reference ',text)
    text = re.sub(r'\bsin-\d{4}-\d+\b|\bs\d{3}\b|\bsinistre_[a-z0-9_]+\b',' claim_reference ',text)
    text = re.sub(r'\b\d{1,4}\s*tu\s*\d{1,4}\b|\bvehicule_[a-z0-9_]+\b',' vehicle_reference ',text)
    return text

def word_present(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(normalize(phrase)) + r'(?!\w)', text))
