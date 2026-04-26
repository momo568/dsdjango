"""
Student #5 — Moteur d'alerting.

Logique :
  1. Lit l'état du système via MetricsStore (Student #3) + eval_results.json (Student #2)
  2. Évalue chaque règle (latence, erreurs, drift, release-gate)
  3. Crée une Alert en DB pour chaque déclenchement
  4. Déduplique (cooldown) pour éviter le spam
  5. Dispatch vers tous les canaux activés

Usage :
  - via management command : `python manage.py run_alerts`
  - via cron / scheduler   : toutes les 1-5 min
  - via GitHub Actions     : après chaque déploiement
"""

import logging
from datetime import timedelta
from typing import Iterable

from django.conf import settings
from django.utils import timezone

from llm_monitor.metrics_store import MetricsStore
from .models import Alert, AlertChannel
from .notifiers import build_notifier, severity_at_least

logger = logging.getLogger('alerting')


# Cooldown : pas plus d'une alerte du même `kind` toutes les N minutes
ALERT_COOLDOWN_MINUTES = getattr(settings, 'ALERTING_COOLDOWN_MINUTES', 10)


class AlertEngine:
    """Moteur central qui évalue les règles et dispatche les alertes."""

    def __init__(self, store: MetricsStore | None = None):
        self.store = store or MetricsStore()

        # Seuils alignés avec llm_monitor.views
        self.t_err_warn   = getattr(settings, 'LLM_HEALTH_ERROR_RATE_DEGRADED', 2.0)
        self.t_err_crit   = getattr(settings, 'LLM_HEALTH_ERROR_RATE_CRITICAL', 10.0)
        self.t_lat_warn   = getattr(settings, 'LLM_HEALTH_LATENCY_DEGRADED',    3000)
        self.t_lat_crit   = getattr(settings, 'LLM_HEALTH_LATENCY_CRITICAL',    10000)
        self.t_drift_warn = getattr(settings, 'LLM_HEALTH_DRIFT_DEGRADED',      1)
        self.t_drift_crit = getattr(settings, 'LLM_HEALTH_DRIFT_CRITICAL',      5)
        self.t_gate       = getattr(settings, 'LLM_RELEASE_GATE_THRESHOLD',     0.40)

    # ──────────────────────────────────────────────────────────────
    # Point d'entrée principal
    # ──────────────────────────────────────────────────────────────

    def run(self, window_minutes: int = 5) -> list[Alert]:
        """Exécute toutes les règles. Retourne la liste des alertes créées."""
        summary = self.store.summary(minutes=window_minutes)
        new_alerts: list[Alert] = []

        for alert in self._evaluate_rules(summary, window_minutes):
            if self._is_in_cooldown(alert.kind, alert.severity):
                logger.info('[Alert] cooldown actif pour %s/%s — skip', alert.kind, alert.severity)
                continue
            alert.save()
            self._dispatch(alert)
            new_alerts.append(alert)

        return new_alerts

    # ──────────────────────────────────────────────────────────────
    # Règles métier
    # ──────────────────────────────────────────────────────────────

    def _evaluate_rules(self, s: dict, window: int) -> Iterable[Alert]:
        # --- Erreurs ---
        err = s.get('error_rate', 0) or 0
        if err > self.t_err_crit:
            yield Alert(
                kind='error_rate', severity='critical',
                title=f"Taux d'erreur critique : {err}%",
                message=(
                    f"Le taux d'erreur sur les {window} dernières minutes est de {err}%, "
                    f"au-dessus du seuil critique de {self.t_err_crit}%. "
                    f"Total : {s.get('error_count', 0)}/{s.get('total_requests', 0)} requêtes."
                ),
                metric_value=err, threshold=self.t_err_crit,
            )
        elif err > self.t_err_warn:
            yield Alert(
                kind='error_rate', severity='warning',
                title=f"Taux d'erreur dégradé : {err}%",
                message=(
                    f"Le taux d'erreur ({err}%) dépasse le seuil de warning ({self.t_err_warn}%). "
                    f"À surveiller."
                ),
                metric_value=err, threshold=self.t_err_warn,
            )

        # --- Latence ---
        lat = s.get('avg_latency_ms', 0) or 0
        if lat > self.t_lat_crit:
            yield Alert(
                kind='latency', severity='critical',
                title=f"Latence critique : {lat:.0f} ms",
                message=(
                    f"Latence moyenne de {lat:.0f} ms sur les {window} dernières minutes, "
                    f"au-dessus du seuil critique ({self.t_lat_crit} ms). "
                    f"Max observé : {s.get('max_latency_ms', 0):.0f} ms."
                ),
                metric_value=lat, threshold=self.t_lat_crit,
            )
        elif lat > self.t_lat_warn:
            yield Alert(
                kind='latency', severity='warning',
                title=f"Latence dégradée : {lat:.0f} ms",
                message=(
                    f"Latence moyenne ({lat:.0f} ms) au-dessus du seuil warning "
                    f"({self.t_lat_warn} ms)."
                ),
                metric_value=lat, threshold=self.t_lat_warn,
            )

        # --- Drift ---
        drift_alerts = s.get('drift_alert_count', 0) or 0
        if drift_alerts > self.t_drift_crit:
            yield Alert(
                kind='drift', severity='critical',
                title=f"{drift_alerts} alertes drift détectées",
                message=(
                    f"{drift_alerts} alertes de drift sémantique en {window} min — "
                    f"le modèle s'éloigne fortement de sa distribution de référence. "
                    f"Score drift moyen : {s.get('avg_drift_score', 0):.3f}, "
                    f"max : {s.get('max_drift_score', 0):.3f}."
                ),
                metric_value=drift_alerts, threshold=self.t_drift_crit,
            )
        elif drift_alerts > self.t_drift_warn:
            yield Alert(
                kind='drift', severity='warning',
                title=f"Drift détecté : {drift_alerts} alertes",
                message=(
                    f"{drift_alerts} alertes drift sur {window} min "
                    f"(seuil warning : {self.t_drift_warn})."
                ),
                metric_value=drift_alerts, threshold=self.t_drift_warn,
            )

        # --- Release gate offline (Student #2) ---
        offline_passed = s.get('offline_passed')
        offline_score  = s.get('offline_score')
        if offline_passed is False and offline_score is not None:
            yield Alert(
                kind='release_gate', severity='critical',
                title=f"Release gate échouée : score {offline_score}",
                message=(
                    f"Le score offline est de {offline_score}, en dessous du seuil "
                    f"de release ({self.t_gate}). Décision : "
                    f"{s.get('offline_decision', 'BLOCK')}. "
                    f"Détail : BLEU={s.get('offline_bleu')} | "
                    f"ROUGE={s.get('offline_rouge')} | Judge={s.get('offline_judge')}. "
                    f"Un rollback peut être envisagé."
                ),
                metric_value=offline_score, threshold=self.t_gate,
            )

    # ──────────────────────────────────────────────────────────────
    # Cooldown & Dispatch
    # ──────────────────────────────────────────────────────────────

    def _is_in_cooldown(self, kind: str, severity: str) -> bool:
        """True si une alerte similaire a été déclenchée dans les N dernières minutes."""
        cutoff = timezone.now() - timedelta(minutes=ALERT_COOLDOWN_MINUTES)
        return Alert.objects.filter(
            kind=kind, severity=severity, triggered_at__gte=cutoff,
        ).exists()

    def _dispatch(self, alert: Alert) -> None:
        """Envoie l'alerte sur tous les canaux activés dont la sévérité min est respectée."""
        channels = AlertChannel.objects.filter(enabled=True)
        notified = []

        if not channels.exists():
            # Fallback : au moins la console
            ConsoleFallback().send(alert)
            notified.append('console (fallback)')

        for ch in channels:
            if not severity_at_least(alert.severity, ch.min_severity):
                continue
            try:
                notifier = build_notifier(ch)
                if notifier.send(alert):
                    notified.append(ch.name)
            except Exception:
                logger.exception('[Dispatch] Échec sur canal %s', ch.name)

        if notified:
            alert.notified_channels = ', '.join(notified)[:255]
            alert.save(update_fields=['notified_channels'])


class ConsoleFallback:
    """Notifier console minimal — utilisé si aucun AlertChannel n'est configuré."""
    def send(self, alert) -> bool:
        from .notifiers import ConsoleNotifier
        return ConsoleNotifier().send(alert)
