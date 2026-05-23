"""Shared inference pipeline class — imported by train_svm.py and tests."""

import html
import re
import unicodedata
from typing import Any

import numpy as np

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_MENTION_RE = re.compile(r"@\w+")
_KEEP_RE = re.compile(r"[^a-záéíóúàèìòùäëïöüâêîôûãõñça-zçśźżółęąćń !?]", re.IGNORECASE)
_SPACE_RE = re.compile(r" {2,}")


def clean_text(raw: str) -> str:
    """Apply the same normalization chain used in preprocess.py."""
    text = unicodedata.normalize("NFKC", raw)
    text = text.lower()
    text = html.unescape(raw)
    text = _URL_RE.sub(" ", text)
    text = _MENTION_RE.sub(" ", text)
    text = _KEEP_RE.sub(" ", text)
    text = _SPACE_RE.sub(" ", text).strip()
    return text


class ToxicPipeline:
    """Self-contained inference object for the ToxicTag API."""

    _VALID_ACTIONS = frozenset({"APPROVE", "REVIEW", "TOXIC_ALERT", "BLOCK"})

    def __init__(
        self,
        vectorizer: Any,
        classifier: Any,
        t_star: float,
        t_review: float,
        t_block: float,
        feature_names: np.ndarray,
    ) -> None:
        self.vectorizer = vectorizer
        self.classifier = classifier
        self.t_star = t_star
        self.t_review = t_review
        self.t_block = t_block
        self.feature_names = feature_names
        svm_core = (
            classifier.calibrated_classifiers_[0].estimator
            if hasattr(classifier, "calibrated_classifiers_")
            else classifier
        )
        self._coef: np.ndarray = np.asarray(svm_core.coef_).ravel()

    def _action(self, score: float) -> str:
        if score >= self.t_block:
            return "BLOCK"
        if score >= self.t_star:
            return "TOXIC_ALERT"
        if score >= self.t_review:
            return "REVIEW"
        return "APPROVE"

    def _top_features(self, tfidf_vec: Any, n: int = 5) -> list[str]:
        arr = np.asarray(tfidf_vec.todense()).ravel()
        active = np.where(arr > 0)[0]
        if len(active) == 0:
            return []
        scores = arr[active] * self._coef[active]
        top_idx = active[np.argsort(scores)[::-1][:n]]
        return [self.feature_names[i] for i in top_idx]

    def predict_one(self, raw_text: str) -> dict:
        cleaned = clean_text(raw_text)
        vec = self.vectorizer.transform([cleaned])
        score = float(self.classifier.predict_proba(vec)[0, 1])
        label = int(score >= self.t_star)
        return {
            "label": label,
            "score": round(score, 6),
            "action": self._action(score),
            "top_features": self._top_features(vec),
        }

    def predict_batch(self, texts: list[str]) -> list[dict]:
        return [self.predict_one(t) for t in texts]
