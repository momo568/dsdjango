"""
Student #3 — Détecteur de drift sémantique

Détecte si la distribution des prompts en production s'éloigne
de la distribution de référence (celle utilisée par Student #2 pour
ses évaluations offline BLEU/ROUGE/LLM-Judge).

Algorithme : cosine similarity sur vecteurs de trigrammes de caractères.
Avantage : CPU-only, < 1ms, aucune dépendance externe.

Drift score → [0.0, 1.0]
  0.0 = distribution identique à la référence (aucun drift)
  1.0 = distribution complètement différente (drift maximal)
"""

import math
import threading
from collections import Counter, deque

from django.conf import settings


class DriftDetector:

    # Seuil configurable dans settings.py — aligné avec Student #2
    ALERT_THRESHOLD:   float = getattr(settings, 'LLM_DRIFT_THRESHOLD', 0.35)
    REFERENCE_WINDOW:  int   = getattr(settings, 'LLM_DRIFT_REFERENCE_WINDOW', 200)
    NGRAM_SIZE:        int   = 3

    def __init__(self):
        self._lock             = threading.Lock()
        self._reference        = deque(maxlen=self.REFERENCE_WINDOW)
        self._centroid         = Counter()
        self._centroid_dirty   = False
        self._n_seen           = 0

    def score(self, fingerprint: str) -> float:
        if not fingerprint:
            return 0.0

        vec = self._vectorize(fingerprint)

        with self._lock:
            # Phase de chauffe : on remplit la référence sans alerter
            if self._n_seen < self.REFERENCE_WINDOW // 4:
                self._add_to_reference(vec)
                self._n_seen += 1
                return 0.0

            centroid = self._get_centroid()
            if not centroid:
                self._add_to_reference(vec)
                return 0.0

            drift = 1.0 - self._cosine(vec, centroid)
            self._add_to_reference(vec)  # mise à jour glissante

        return max(0.0, min(1.0, drift))

    def reset(self):
        """
        Réinitialise la fenêtre de référence.
        À appeler après un changement intentionnel de modèle ou de prompt
        (typiquement déclenché par Student #5 après une release).
        """
        with self._lock:
            self._reference.clear()
            self._centroid       = Counter()
            self._centroid_dirty = False
            self._n_seen         = 0

    @property
    def reference_size(self) -> int:
        with self._lock:
            return len(self._reference)

    # ------------------------------------------------------------------
    # Méthodes internes
    # ------------------------------------------------------------------

    def _vectorize(self, text: str) -> Counter:
        return Counter(
            text[i:i + self.NGRAM_SIZE]
            for i in range(len(text) - self.NGRAM_SIZE + 1)
        )

    def _add_to_reference(self, vec: Counter):
        self._reference.append(vec)
        self._centroid_dirty = True

    def _get_centroid(self) -> Counter:
        if not self._centroid_dirty:
            return self._centroid

        n = len(self._reference)
        if n == 0:
            return Counter()

        centroid = Counter()
        for vec in self._reference:
            centroid.update(vec)
        for k in centroid:
            centroid[k] /= n

        self._centroid       = centroid
        self._centroid_dirty = False
        return centroid

    @staticmethod
    def _cosine(a: Counter, b: Counter) -> float:
        if not a or not b:
            return 0.0
        dot    = sum(a[k] * b[k] for k in a if k in b)
        norm_a = math.sqrt(sum(v * v for v in a.values()))
        norm_b = math.sqrt(sum(v * v for v in b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)