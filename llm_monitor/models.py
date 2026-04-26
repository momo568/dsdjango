"""
Student #3 — Modèles Django

InferenceMetric : une ligne par requête LLM en production.
Écrit par le middleware, lu par le dashboard (Student #4)
et le système d'alertes (Student #5).
"""

from django.db import models
from django.utils import timezone


class InferenceMetric(models.Model):

    recorded_at       = models.DateTimeField(default=timezone.now, db_index=True)
    path              = models.CharField(max_length=255, db_index=True)
    method            = models.CharField(max_length=10, default='POST')
    status_code       = models.PositiveSmallIntegerField(default=200)

    # Latence
    latency_ms        = models.FloatField()

    # Erreurs
    is_error          = models.BooleanField(default=False, db_index=True)
    exception         = models.CharField(max_length=128, blank=True, default='')

    # Tokens (depuis le body de la réponse LLM)
    prompt_tokens     = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens      = models.PositiveIntegerField(default=0)

    # Drift sémantique
    drift_score       = models.FloatField(default=0.0)
    drift_alert       = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes  = [
            models.Index(fields=['recorded_at', 'is_error']),
            models.Index(fields=['recorded_at', 'drift_alert']),
            models.Index(fields=['path', 'recorded_at']),
        ]
        verbose_name        = 'Inference Metric'
        verbose_name_plural = 'Inference Metrics'

    def __str__(self):
        return f"[{self.recorded_at:%H:%M:%S}] {self.path} — {self.latency_ms:.0f}ms drift={self.drift_score:.3f}"