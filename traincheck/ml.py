"""Sentence-level ML baseline: TF-IDF + logistic regression.

This is the "model proposes, rules decide" layer, implemented with the
smallest honest model that can do the job:

- Training data: sentence_dataset() rows from annotations.py — one row
  per sentence, labeled with the rubric items it evidences.
- Model: TF-IDF word 1-2 grams + one-vs-rest logistic regression,
  fixed random_state, frozen default threshold 0.5. Deterministic:
  same rows + same code = same model.
- The classifier NEVER sets an item state. predict_candidates() returns
  candidate sentences per item with confidences; the app shows them as
  "model-surfaced, unverified" and they do not count toward
  completeness. The two legitimate upgrades from ML are:
  (a) distillation — promote reviewed phrases into deterministic rules;
  (b) triage — surface sentences a human reviewer should check.

Labels need both positive and negative examples in training; a label
that is all-positive or all-negative raises a clear error instead of
silently training a degenerate classifier.
"""

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.multiclass import OneVsRestClassifier
from sklearn.preprocessing import MultiLabelBinarizer

MODEL_NAME = "tfidf-lr-v1"
DEFAULT_THRESHOLD = 0.5


def _features(row):
    return f"{row['text']} § {row.get('section', '')}"


def train_sentence_classifier(rows, labels=None):
    """Train on annotation dataset rows. Returns a model bundle dict."""
    if not rows:
        raise ValueError("no training rows")
    y_lists = [sorted(set(r["items"])) for r in rows]
    mlb = MultiLabelBinarizer(classes=sorted(labels) if labels else None)
    Y = mlb.fit_transform(y_lists)
    degenerate = []
    for j, label in enumerate(mlb.classes_):
        pos = int(Y[:, j].sum())
        if pos == 0 or pos == len(rows):
            degenerate.append(label)
    if degenerate:
        raise ValueError(
            f"labels need both positive and negative examples: {degenerate}")
    vec = TfidfVectorizer(lowercase=True, ngram_range=(1, 2),
                          sublinear_tf=True, min_df=1, max_features=20000)
    Xv = vec.fit_transform([_features(r) for r in rows])
    clf = OneVsRestClassifier(LogisticRegression(
        max_iter=1000, class_weight="balanced", random_state=0,
        solver="lbfgs", C=1.0))
    clf.fit(Xv, Y)
    return {"model_name": MODEL_NAME, "vectorizer": vec,
            "binarizer_classes": list(mlb.classes_), "classifier": clf,
            "threshold": DEFAULT_THRESHOLD}


def _proba_matrix(bundle, texts):
    Xv = bundle["vectorizer"].transform(texts)
    proba = bundle["classifier"].predict_proba(Xv)
    if isinstance(proba, list):
        proba = np.column_stack([
            p[:, 1] if p.shape[1] > 1 else p[:, 0] for p in proba])
    return np.asarray(proba)


def predict_candidates(bundle, doc):
    """Per-item candidate sentences for one parsed document.

    Returns {item_id: [evidence]} where evidence = {quote, section,
    sentence_id, source, confidence}. Candidates never change an item's
    state on their own; they are surfaced for review or distillation.
    """
    sents = [(s["title"], t, sid) for s in doc["sections"]
             for t, sid in zip(s["sentences"], s["sentence_ids"])]
    if not sents:
        return {}
    texts = [f"{t} § {title}" for title, t, _ in sents]
    proba = _proba_matrix(bundle, texts)
    out = {}
    for j, label in enumerate(bundle["binarizer_classes"]):
        evs = []
        for i, (title, text, sid) in enumerate(sents):
            p = float(proba[i, j])
            if p >= bundle["threshold"]:
                evs.append({"quote": text, "section": title, "sentence_id": sid,
                            "source": f"ml:{bundle['model_name']}",
                            "confidence": round(p, 3)})
        if evs:
            out[label] = evs
    return out


def distill_rule_candidates(bundle, top_n=15):
    """Top discriminative phrases per label, for HUMAN review.

    Returns {label: [{phrase, weight}]}. These are candidates only:
    promoting one into a deterministic rule is a human decision, made
    by checking the phrase against real policies and re-measuring.
    A distilled phrase that fires wrongly is worse than no phrase.
    """
    feature_names = bundle["vectorizer"].get_feature_names_out()
    out = {}
    for j, label in enumerate(bundle["binarizer_classes"]):
        coef = bundle["classifier"].estimators_[j].coef_[0]
        top = np.argsort(coef)[::-1][:top_n]
        out[label] = [{"phrase": str(feature_names[i]),
                       "weight": round(float(coef[i]), 3)}
                      for i in top if coef[i] > 0]
    return out


def save_bundle(bundle, path):
    joblib.dump(bundle, path)


def load_bundle(path):
    return joblib.load(path)
