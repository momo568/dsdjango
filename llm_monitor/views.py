"""
Student #3 — API Views de monitoring online

Endpoints utilisés par :
- Student #4 (Dashboard) : /summary/ et /timeseries/
- Student #5 (Alertes + Release) : /health/
- Student #2 (CI pipeline) : /health/ comme release gate en production

Tous les endpoints nécessitent le header : X-Monitor-Api-Key
"""

import logging
from datetime import datetime, timezone

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .metrics_store import MetricsStore
from .drift_detector import DriftDetector

logger  = logging.getLogger('llm_monitor')
_store  = MetricsStore()
_drift  = DriftDetector()
API_KEY = getattr(settings, 'LLM_MONITOR_API_KEY', 'dev-key')

# Seuils lus depuis settings (alignés avec Student #2)
THRESHOLD_ERROR_DEGRADED  = getattr(settings, 'LLM_HEALTH_ERROR_RATE_DEGRADED', 2.0)
THRESHOLD_ERROR_CRITICAL  = getattr(settings, 'LLM_HEALTH_ERROR_RATE_CRITICAL', 10.0)
THRESHOLD_LATENCY_DEGRADED= getattr(settings, 'LLM_HEALTH_LATENCY_DEGRADED',    3000)
THRESHOLD_LATENCY_CRITICAL= getattr(settings, 'LLM_HEALTH_LATENCY_CRITICAL',    10000)
THRESHOLD_DRIFT_DEGRADED  = getattr(settings, 'LLM_HEALTH_DRIFT_DEGRADED',      1)
THRESHOLD_DRIFT_CRITICAL  = getattr(settings, 'LLM_HEALTH_DRIFT_CRITICAL',      5)
RELEASE_GATE_THRESHOLD    = getattr(settings, 'LLM_RELEASE_GATE_THRESHOLD',     0.40)


def _auth(view_fn):
    def wrapper(request, *args, **kwargs):
        if request.headers.get('X-Monitor-Api-Key', '') != API_KEY:
            return JsonResponse({'error': 'Non autorisé — header X-Monitor-Api-Key requis'}, status=403)
        return view_fn(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────
# GET /api/monitor/summary/?minutes=60
# ─────────────────────────────────────────────────────────────────────

@_auth
def summary_view(request):
    """
    Résumé agrégé — utilisé par Student #4 pour les cartes du dashboard.

    Retourne les métriques online + le dernier score offline de Student #2
    (lu depuis eval_results.json).
    """
    minutes = _parse_int(request.GET.get('minutes', '60'), 60, 1, 1440)
    data    = _store.summary(minutes=minutes)
    data['health']       = _health_status(data)
    data['generated_at'] = datetime.now(timezone.utc).isoformat()
    return JsonResponse(data)


# ─────────────────────────────────────────────────────────────────────
# GET /api/monitor/timeseries/?metric=latency|drift&minutes=60
# ─────────────────────────────────────────────────────────────────────

@_auth
def timeseries_view(request):
    """Série temporelle pour les graphiques du dashboard (Student #4)."""
    minutes = _parse_int(request.GET.get('minutes', '60'), 60, 1, 1440)
    metric  = request.GET.get('metric', 'latency')

    if metric == 'drift':
        qs     = _store.drift_timeseries(minutes=minutes)
        series = [{'bucket': r['bucket'].isoformat(), 'value': round(r['avg_drift'], 4)} for r in qs]
    else:
        qs     = _store.latency_timeseries(minutes=minutes)
        series = [{'bucket': r['bucket'].isoformat(), 'value': round(r['avg_latency'], 1)} for r in qs]

    return JsonResponse({
        'metric':         metric,
        'window_minutes': minutes,
        'series':         series,
        'generated_at':   datetime.now(timezone.utc).isoformat(),
    })


# ─────────────────────────────────────────────────────────────────────
# GET /api/monitor/recent/?minutes=10&limit=50
# ─────────────────────────────────────────────────────────────────────

@_auth
def recent_view(request):
    """Dernières lignes brutes — pour le flux live du dashboard (Student #4)."""
    minutes = _parse_int(request.GET.get('minutes', '10'), 10, 1, 60)
    limit   = _parse_int(request.GET.get('limit', '50'),   50, 1, 500)

    rows = _store.recent(minutes=minutes)[:limit]
    return JsonResponse({
        'count': len(rows),
        'rows': [
            {
                'id':          m.id,
                'recorded_at': m.recorded_at.isoformat(),
                'path':        m.path,
                'status_code': m.status_code,
                'latency_ms':  m.latency_ms,
                'is_error':    m.is_error,
                'total_tokens':m.total_tokens,
                'drift_score': m.drift_score,
                'drift_alert': m.drift_alert,
            }
            for m in rows
        ],
    })


# ─────────────────────────────────────────────────────────────────────
# GET /api/monitor/health/
# ─────────────────────────────────────────────────────────────────────

@_auth
def health_view(request):
    """
    Sonde de santé — utilisée par Student #5 (alertes) et Student #2 (CI).

    Décision combinée :
      1. Métriques online (latence, erreurs, drift)    → Student #3
      2. Score offline de la ReleaseGate               → Student #2

    Retourne HTTP 200 si healthy/degraded, HTTP 503 si critical.

    Exemple d'utilisation dans le CI de Student #2 :
      curl -f -H "X-Monitor-Api-Key: xxx" https://monapp.com/api/monitor/health/
    """
    data        = _store.summary(minutes=5)
    online_status = _health_status(data)

    # ✅ Intégration Student #2 — si le score offline échoue → critical
    offline_score   = data.get('offline_score')
    offline_passed  = data.get('offline_passed')
    offline_decision= data.get('offline_decision', 'UNKNOWN')

    # Si le score offline existe et est bloquant → on force critical
    if offline_passed is False and offline_score is not None:
        final_status = 'critical'
        reason = (
            f"Score offline insuffisant : {offline_score} < {RELEASE_GATE_THRESHOLD} "
            f"(formule Student #2 : BLEU×0.2 + ROUGE×0.3 + Judge×0.5)"
        )
    else:
        final_status = online_status
        reason = _health_reason(data, online_status)

    http_code = 503 if final_status == 'critical' else 200

    return JsonResponse({
        # Statut global
        'health':           final_status,
        'reason':           reason,
        # Métriques online (Student #3)
        'online': {
            'error_rate':        data['error_rate'],
            'avg_latency_ms':    data['avg_latency_ms'],
            'drift_alerts_5m':   data['drift_alert_count'],
            'total_requests_5m': data['total_requests'],
        },
        # Score offline (Student #2)
        'offline': {
            'score':        offline_score,
            'passed':       offline_passed,
            'decision':     offline_decision,
            'bleu':         data.get('offline_bleu'),
            'rouge':        data.get('offline_rouge'),
            'judge':        data.get('offline_judge'),
            'formula':      data.get('offline_formula'),
            'evaluated_at': data.get('offline_evaluated_at'),
        },
        'checked_at': datetime.now(timezone.utc).isoformat(),
    }, status=http_code)


# ─────────────────────────────────────────────────────────────────────
# POST /api/monitor/drift/reset/
# ─────────────────────────────────────────────────────────────────────

@csrf_exempt
@_auth
def drift_reset_view(request):
    """
    Réinitialise la fenêtre de référence du drift detector.
    À appeler après une mise à jour intentionnelle du modèle ou du prompt.
    Typiquement déclenché par Student #5 après une release réussie.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST requis'}, status=405)

    _drift.reset()
    logger.warning('[Monitor] Drift detector réinitialisé via API')
    return JsonResponse({
        'status':   'ok',
        'message':  'Fenêtre de référence drift réinitialisée',
        'reset_at': datetime.now(timezone.utc).isoformat(),
    })


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _health_status(data: dict) -> str:
    e = data.get('error_rate', 0)
    l = data.get('avg_latency_ms', 0)
    d = data.get('drift_alert_count', 0)

    if e > THRESHOLD_ERROR_CRITICAL or l > THRESHOLD_LATENCY_CRITICAL or d > THRESHOLD_DRIFT_CRITICAL:
        return 'critical'
    if e > THRESHOLD_ERROR_DEGRADED or l > THRESHOLD_LATENCY_DEGRADED or d > THRESHOLD_DRIFT_DEGRADED:
        return 'degraded'
    return 'healthy'


def _health_reason(data: dict, status: str) -> str:
    if status == 'healthy':
        return 'Tous les indicateurs sont dans les seuils normaux'
    reasons = []
    if data.get('error_rate', 0) > THRESHOLD_ERROR_DEGRADED:
        reasons.append(f"taux d'erreur {data['error_rate']}%")
    if data.get('avg_latency_ms', 0) > THRESHOLD_LATENCY_DEGRADED:
        reasons.append(f"latence moyenne {data['avg_latency_ms']}ms")
    if data.get('drift_alert_count', 0) > THRESHOLD_DRIFT_DEGRADED:
        reasons.append(f"{data['drift_alert_count']} alertes drift")
    return ' | '.join(reasons) if reasons else status


def _parse_int(value, default, lo, hi):
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default