"""
Student #5 — Modèles pour le système d'alertes & release.

- Alert         : une alerte déclenchée (latence/erreur/drift/release-gate)
- AlertChannel  : canal de notification configurable (Slack/Email/Console)
- ReleaseEvent  : trace d'un déploiement / rollback (audit trail)
"""

from django.db import models


class AlertChannel(models.Model):
    """Canal de notification — configurable depuis l'admin."""

    KIND_CHOICES = [
        ('console', 'Console / Logs'),
        ('slack',   'Slack Webhook'),
        ('email',   'Email SMTP'),
    ]

    name        = models.CharField(max_length=100, unique=True)
    kind        = models.CharField(max_length=16, choices=KIND_CHOICES, default='console')
    enabled     = models.BooleanField(default=True)
    # Pour slack : URL webhook. Pour email : adresses séparées par des virgules.
    target      = models.CharField(max_length=500, blank=True, default='')
    # Severity minimale pour déclencher ce canal
    min_severity = models.CharField(
        max_length=16,
        choices=[('info', 'info'), ('warning', 'warning'), ('critical', 'critical')],
        default='warning',
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Alert Channel'
        verbose_name_plural = 'Alert Channels'

    def __str__(self):
        return f"{self.name} ({self.kind}) — {'on' if self.enabled else 'off'}"


class Alert(models.Model):
    """Une alerte déclenchée par le moteur d'alerting."""

    SEVERITY_CHOICES = [
        ('info',     'Info'),
        ('warning',  'Warning'),
        ('critical', 'Critical'),
    ]

    KIND_CHOICES = [
        ('error_rate',   "Taux d'erreur"),
        ('latency',      'Latence élevée'),
        ('drift',        'Drift sémantique'),
        ('release_gate', 'Release gate échouée'),
        ('rollback',     'Rollback déclenché'),
        ('health',       'Health check'),
    ]

    triggered_at = models.DateTimeField(auto_now_add=True, db_index=True)
    kind         = models.CharField(max_length=32, choices=KIND_CHOICES, db_index=True)
    severity     = models.CharField(max_length=16, choices=SEVERITY_CHOICES, default='warning', db_index=True)
    title        = models.CharField(max_length=200)
    message      = models.TextField()

    # Snapshot au moment de l'alerte (pour reproductibilité)
    metric_value = models.FloatField(null=True, blank=True)
    threshold    = models.FloatField(null=True, blank=True)

    # État de l'alerte
    acknowledged = models.BooleanField(default=False, db_index=True)
    resolved_at  = models.DateTimeField(null=True, blank=True)

    # Notification
    notified_channels = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-triggered_at']
        indexes = [
            models.Index(fields=['triggered_at', 'severity']),
            models.Index(fields=['kind', 'triggered_at']),
        ]
        verbose_name        = 'Alert'
        verbose_name_plural = 'Alerts'

    def __str__(self):
        return f"[{self.severity.upper()}] {self.title} @ {self.triggered_at:%Y-%m-%d %H:%M}"


class ReleaseEvent(models.Model):
    """Trace d'un événement de release : déploiement ou rollback."""

    EVENT_CHOICES = [
        ('deploy',   'Déploiement'),
        ('rollback', 'Rollback'),
        ('blocked',  'Release bloquée'),
    ]

    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)
    event       = models.CharField(max_length=16, choices=EVENT_CHOICES, db_index=True)
    version     = models.CharField(max_length=64, blank=True, default='')
    previous_version = models.CharField(max_length=64, blank=True, default='')

    # Score offline qui a justifié la décision
    offline_score = models.FloatField(null=True, blank=True)
    threshold     = models.FloatField(null=True, blank=True)

    triggered_by  = models.CharField(max_length=64, blank=True, default='ci')  # 'ci', 'manual', 'auto-rollback'
    reason        = models.TextField(blank=True, default='')
    success       = models.BooleanField(default=True)
    git_sha       = models.CharField(max_length=40, blank=True, default='')

    class Meta:
        ordering = ['-occurred_at']
        verbose_name        = 'Release Event'
        verbose_name_plural = 'Release Events'

    def __str__(self):
        return f"[{self.event}] v{self.version or '?'} @ {self.occurred_at:%Y-%m-%d %H:%M}"
