import json
import os
from functools import lru_cache
from pathlib import Path
from .text import classifier_text

ROOT = Path(__file__).resolve().parents[2] / 'ml'

@lru_cache(maxsize=1)
def load_model():
    config = json.loads((ROOT / 'artifacts' / 'selected.json').read_text(encoding='utf-8'))
    path = ROOT / config['path']
    if config['engine'] != 'tfidf':
        import torch
        torch.set_num_threads(min(4,torch.get_num_threads()))
    if config['engine'] == 'tfidf':
        import joblib
        model = joblib.load(path)
    elif config['engine'] == 'ensemble':
        import joblib
        from setfit import SetFitModel
        model = (joblib.load(ROOT/config['tfidf']),SetFitModel.from_pretrained(str(path),local_files_only=True))
    elif config['engine'] == 'frozen':
        import joblib
        from sentence_transformers import SentenceTransformer
        model = (SentenceTransformer(str(path),local_files_only=True),joblib.load(ROOT/config['head']))
    else:
        from setfit import SetFitModel
        model = SetFitModel.from_pretrained(str(path), local_files_only=True)
    return config, model

def predict(text):
    config, model = load_model()
    question = classifier_text(text)
    if config['engine'] == 'tfidf':
        values = model.predict_proba([question])[0]
        labels = model.classes_
    elif config['engine'] == 'ensemble':
        tfidf, transformer=model
        a=tfidf.predict_proba([question])[0]
        b=transformer.predict_proba([question])[0]
        if hasattr(b,'numpy'):
            b=b.numpy()
        labels=tfidf.classes_
        if list(labels)!=transformer.labels:
            raise ValueError('Classifier label order mismatch')
        weight=config['weight'];values=weight*a+(1-weight)*b
    elif config['engine'] == 'frozen':
        encoder,head=model
        values=head.predict_proba(encoder.encode([question]))[0]
        labels=head.classes_
    else:
        values = model.predict_proba([question])[0]
        if hasattr(values, 'numpy'):
            values = values.numpy()
        labels = model.labels
    ranked = sorted(zip(labels, map(float, values)), key=lambda x: -x[1])
    label, score = ranked[0]
    accepted = label != 'unsupported' and score >= config['threshold'] and score-ranked[1][1] >= config.get('margin', 0)
    return {'label': label, 'score': score, 'accepted': accepted, 'ranking': ranked[:3], 'engine': config['name']}
