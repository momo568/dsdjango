"""
Service de Release & Rollback.

Responsabilités :
  - Lire eval_results.json (Student #2) pour décider DEPLOY / BLOCK
  - Tracer chaque événement (deploy/rollback/blocked) dans ReleaseEvent
  - Déclencher un rollback automatique si la santé en prod se dégrade
  - Exposer une CLI utilisable depuis GitHub Actions

Le rollback se fait via un script shell (rollback.sh) qui :
  - revert le dernier commit Git
  - ou redéploie le tag précédent
  - ou notifie un système de déploiement externe (k8s, Heroku, etc.)
"""

import json
import logging
import subprocess
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from .models import Alert, ReleaseEvent

logger = logging.getLogger('alerting')


EVAL_RESULTS_PATH: Path = getattr(
    settings, 'LLM_EVAL_RESULTS_PATH', Path('eval_results.json')
)
RELEASE_THRESHOLD: float = getattr(
    settings, 'LLM_RELEASE_GATE_THRESHOLD', 0.55
)
ROLLBACK_SCRIPT: Path = getattr(
    settings, 'ROLLBACK_SCRIPT_PATH', Path(settings.BASE_DIR) / 'scripts' / 'rollback.sh'
)


class ReleaseService:
    """Centralise les décisions de release et le rollback."""

    # ──────────────────────────────────────────────────────────────
    # Lecture du score offline
    # ──────────────────────────────────────────────────────────────

    def read_offline_score(self) -> dict | None:
        path = Path(EVAL_RESULTS_PATH)
        if not path.exists():
            logger.warning('[Release] eval_results.json introuvable : %s', path)
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            logger.exception('[Release] Lecture eval_results.json échouée')
            return None

    # ──────────────────────────────────────────────────────────────
    # Décision de release
    # ──────────────────────────────────────────────────────────────

    def decide(self, version: str = '', git_sha: str = '', triggered_by: str = 'ci') -> ReleaseEvent:
        """
        Décide DEPLOY / BLOCK selon eval_results.json.
        Crée un ReleaseEvent pour tracer la décision.
        """
        offline = self.read_offline_score()

        if not offline:
            event = ReleaseEvent.objects.create(
                event='blocked',
                version=version, git_sha=git_sha, triggered_by=triggered_by,
                offline_score=None, threshold=RELEASE_THRESHOLD,
                success=False,
                reason='eval_results.json absent — pipeline d\'évaluation non exécuté',
            )
            self._alert_release_blocked(event)
            return event

        score  = offline.get('average_score', 0.0)
        passed = offline.get('passed', False)

        if passed and score >= RELEASE_THRESHOLD:
            event = ReleaseEvent.objects.create(
                event='deploy',
                version=version, git_sha=git_sha, triggered_by=triggered_by,
                offline_score=score, threshold=RELEASE_THRESHOLD,
                success=True,
                reason=f"Score {score} >= seuil {RELEASE_THRESHOLD}. Décision : DEPLOY",
            )
            logger.info('[Release] ✅ DEPLOY autorisé : score=%s', score)
            return event

        # Bloqué
        event = ReleaseEvent.objects.create(
            event='blocked',
            version=version, git_sha=git_sha, triggered_by=triggered_by,
            offline_score=score, threshold=RELEASE_THRESHOLD,
            success=False,
            reason=f"Score {score} < seuil {RELEASE_THRESHOLD}. Décision : BLOCK",
        )
        self._alert_release_blocked(event)
        return event

    # ──────────────────────────────────────────────────────────────
    # Rollback
    # ──────────────────────────────────────────────────────────────

    def rollback(self, reason: str = '', triggered_by: str = 'auto-rollback',
                 dry_run: bool = False) -> ReleaseEvent:
        """
        Déclenche un rollback. Tente d'exécuter scripts/rollback.sh.
        Si le script est absent → simulation (event créé mais success=False).
        """
        previous = self._last_successful_deploy()
        prev_version = previous.version if previous else ''

        cmd_output = ''
        success    = False

        if dry_run:
            cmd_output = '[DRY-RUN] script de rollback non exécuté'
            success = True
        elif Path(ROLLBACK_SCRIPT).exists():
            try:
                result = subprocess.run(
                    [str(ROLLBACK_SCRIPT), prev_version or 'HEAD~1'],
                    capture_output=True, text=True, timeout=120,
                )
                cmd_output = (result.stdout + '\n' + result.stderr).strip()[:2000]
                success    = (result.returncode == 0)
            except Exception as e:
                cmd_output = f'Exception : {e}'
                success    = False
        else:
            cmd_output = f'Script rollback introuvable : {ROLLBACK_SCRIPT}'
            success    = False

        event = ReleaseEvent.objects.create(
            event='rollback',
            version=prev_version, previous_version=prev_version,
            triggered_by=triggered_by,
            success=success,
            reason=(reason or 'Rollback déclenché') + '\n\n--- Output ---\n' + cmd_output,
        )

        self._alert_rollback(event)
        return event

    def auto_rollback_if_unhealthy(self, window_minutes: int = 10,
                                   dry_run: bool = False) -> ReleaseEvent | None:
        """
        Vérifie la santé récente. Si critique → rollback automatique.
        À appeler périodiquement (cron / GitHub Actions / scheduler).
        """
        from llm_monitor.metrics_store import MetricsStore
        summary = MetricsStore().summary(minutes=window_minutes)
        health  = summary.get('health', 'healthy')

        if health != 'critical':
            return None

        # On ne rollback pas si on vient déjà de le faire (cooldown 30 min)
        recent = ReleaseEvent.objects.filter(
            event='rollback',
            occurred_at__gte=timezone.now() - timedelta(minutes=30),
        ).exists()
        if recent:
            logger.info('[Auto-rollback] cooldown actif — skip')
            return None

        reason = (
            f"Auto-rollback : santé prod = critical. "
            f"error_rate={summary.get('error_rate')}% | "
            f"latence={summary.get('avg_latency_ms')}ms | "
            f"drift_alerts={summary.get('drift_alert_count')}"
        )
        return self.rollback(reason=reason, triggered_by='auto-rollback', dry_run=dry_run)

    # ──────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────

    def _last_successful_deploy(self) -> ReleaseEvent | None:
        return (
            ReleaseEvent.objects
            .filter(event='deploy', success=True)
            .order_by('-occurred_at')
            .first()
        )

    def _alert_release_blocked(self, event: ReleaseEvent):
        from .engine import AlertEngine
        target = event.version or '?'
        prefix = '' if target.startswith('v') else 'v'
        alert = Alert.objects.create(
            kind='release_gate', severity='critical',
            title=f"Release bloquée : {prefix}{target}",
            message=event.reason,
            metric_value=event.offline_score, threshold=event.threshold,
        )
        AlertEngine()._dispatch(alert)

    def _alert_rollback(self, event: ReleaseEvent):
        from .engine import AlertEngine
        severity = 'critical' if event.success else 'warning'
        target = event.version or 'HEAD~1'
        # Évite "vv1.0" si la version commence déjà par 'v'
        prefix = '' if target.startswith('v') else 'v'
        alert = Alert.objects.create(
            kind='rollback', severity=severity,
            title=f"Rollback {'réussi' if event.success else 'ÉCHOUÉ'} → {prefix}{target}",
            message=event.reason,
        )
        AlertEngine()._dispatch(alert)
