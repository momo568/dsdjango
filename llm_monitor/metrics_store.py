"""
Student #3 — MetricsStore

Façade ORM pour écrire et lire les métriques online.

Intégration avec Student #2 :
  Le fichier eval_results.json produit par ReleaseGate.export_results()
  est lu ici pour enrichir le /health/ endpoint avec le score offline.
  Cela permet une décision de santé qui combine :
    - métriques online  (latence, erreurs, drift)  → Student #3
    - score offline     (BLEU/ROUGE/Judge)          → Student #2
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger('llm_monitor')

# Chemin vers le fichier JSON exporté par Student #2
EVAL_RESULTS_PATH: Path = getattr(
    settings, 'LLM_EVAL_RESULTS_PATH', Path('eval_results.json')
)


class MetricsStore:

    def record(self, metric: dict[str, Any]) -> None:
        """Persiste une métrique. Ne lève jamais d'exception."""
        try:
            from .models import InferenceMetric
            InferenceMetric.objects.create(
                path              = metric.get('path', ''),
                method            = metric.get('method', 'POST'),
                status_code       = metric.get('status_code', 200),
                latency_ms        = metric.get('latency_ms', 0.0),
                is_error          = metric.get('is_error', False),
                prompt_tokens     = metric.get('prompt_tokens', 0),
                completion_tokens = metric.get('completion_tokens', 0),
                total_tokens      = metric.get('total_tokens', 0),
                drift_score       = metric.get('drift_score', 0.0),
                drift_alert       = metric.get('drift_alert', False),
                exception         = metric.get('exception', ''),
            )
        except Exception:
            logger.exception('[MetricsStore] Échec de persistence')

    # ------------------------------------------------------------------
    # Lecture — utilisé par les views
    # ------------------------------------------------------------------

    def recent(self, minutes: int = 60):
        from .models import InferenceMetric
        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return InferenceMetric.objects.filter(recorded_at__gte=since).order_by('-recorded_at')

    def summary(self, minutes: int = 60) -> dict:
        """
        Résumé agrégé des métriques online.
        Inclut le score offline de Student #2 si eval_results.json est disponible.
        """
        from django.db.models import Avg, Count, Max, Min, Q
        from .models import InferenceMetric

        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        qs    = InferenceMetric.objects.filter(recorded_at__gte=since)

        agg = qs.aggregate(
            total          = Count('id'),
            errors         = Count('id', filter=Q(is_error=True)),
            avg_latency    = Avg('latency_ms'),
            max_latency    = Max('latency_ms'),
            min_latency    = Min('latency_ms'),
            avg_drift      = Avg('drift_score'),
            max_drift      = Max('drift_score'),
            drift_alerts   = Count('id', filter=Q(drift_alert=True)),
            avg_tokens     = Avg('total_tokens'),
        )

        total      = agg['total'] or 1
        error_rate = round((agg['errors'] or 0) / total * 100, 2)

        result = {
            'window_minutes':    minutes,
            'total_requests':    agg['total'] or 0,
            'error_count':       agg['errors'] or 0,
            'error_rate':        error_rate,
            'avg_latency_ms':    round(agg['avg_latency'] or 0, 1),
            'max_latency_ms':    round(agg['max_latency'] or 0, 1),
            'min_latency_ms':    round(agg['min_latency'] or 0, 1),
            'avg_drift_score':   round(agg['avg_drift'] or 0, 4),
            'max_drift_score':   round(agg['max_drift'] or 0, 4),
            'drift_alert_count': agg['drift_alerts'] or 0,
            'avg_tokens':        round(agg['avg_tokens'] or 0, 1),
        }

        # ✅ Intégration Student #2 — lecture du dernier score offline
        offline = self._read_offline_score()
        if offline:
            result['offline_score']    = offline.get('average_score')
            result['offline_passed']   = offline.get('passed')
            result['offline_decision'] = offline.get('decision')
            result['offline_bleu']     = offline.get('bleu_score')
            result['offline_rouge']    = offline.get('rouge_score')
            result['offline_judge']    = offline.get('llm_judge_score')
            result['offline_formula']  = offline.get('formula')
            result['offline_evaluated_at'] = offline.get('evaluated_at')

        # ✅ Student #4 — Calcul du statut de santé combiné
        # Seuils critiques online
        is_critical = (
            error_rate > 10  # > 10% erreurs
            or result['avg_latency_ms'] > 10000  # > 10s
            or result['drift_alert_count'] > 5   # > 5 alertes drift
        )
        # Seuils dégradés online
        is_degraded = (
            error_rate > 2  # > 2%
            or result['avg_latency_ms'] > 3000  # > 3s
            or result['drift_alert_count'] > 1  # > 1 alerte
        )
        # Offline failed gate
        offline_failed = offline and not offline.get('passed', True)
        
        # Logique combinée
        if is_critical or offline_failed:
            result['health'] = 'critical'
        elif is_degraded:
            result['health'] = 'degraded'
        else:
            result['health'] = 'healthy'

        return result

    def latency_timeseries(self, minutes: int = 60):
        from django.db.models import Avg
        from django.db.models.functions import TruncMinute
        from .models import InferenceMetric

        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return (
            InferenceMetric.objects
            .filter(recorded_at__gte=since)
            .annotate(bucket=TruncMinute('recorded_at'))
            .values('bucket')
            .annotate(avg_latency=Avg('latency_ms'))
            .order_by('bucket')
        )

    def drift_timeseries(self, minutes: int = 60):
        from django.db.models import Avg
        from django.db.models.functions import TruncMinute
        from .models import InferenceMetric

        since = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        return (
            InferenceMetric.objects
            .filter(recorded_at__gte=since)
            .annotate(bucket=TruncMinute('recorded_at'))
            .values('bucket')
            .annotate(avg_drift=Avg('drift_score'))
            .order_by('bucket')
        )

    # ------------------------------------------------------------------
    # Intégration Student #2
    # ------------------------------------------------------------------

    def _read_offline_score(self) -> dict | None:
        """
        Lit le fichier eval_results.json produit par ReleaseGate.export_results().
        Retourne None si le fichier n'existe pas encore.
        """
        try:
            path = Path(EVAL_RESULTS_PATH)
            if not path.exists():
                return None
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            logger.warning('[MetricsStore] Impossible de lire eval_results.json')
            return None