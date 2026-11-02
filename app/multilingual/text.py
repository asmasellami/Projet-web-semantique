import re
import unicodedata

def normalize(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', text.replace('’', "'")).strip()

def classifier_text(text):
    """Names/numeric identifiers are slots, not intent features. No numeral transliteration."""
    text = normalize(text)
    text = re.sub(r'\b(?:auto|hab|sante)-\d{4}-\d+\b|\bsin-\d{4}-\d+\b|\bs\d{3}\b', ' reference ', text)
    return text

def word_present(text, phrase):
    return bool(re.search(r'(?<!\w)' + re.escape(normalize(phrase)) + r'(?!\w)', text))
