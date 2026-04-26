"""
Student #5 — Vues API pour l'alerting + démo.
"""

from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Alert, ReleaseEvent

API_KEY = getattr(settings, 'LLM_MONITOR_API_KEY', 'dev-key')


def _auth(view_fn):
    """Réutilise la même clé API que llm_monitor pour cohérence."""
    def wrapper(request, *args, **kwargs):
        if request.headers.get('X-Monitor-Api-Key', '') != API_KEY:
            return JsonResponse(
                {'error': 'Non autorisé — header X-Monitor-Api-Key requis'},
                status=403,
            )
        return view_fn(request, *args, **kwargs)
    return wrapper


# ─────────────────────────────────────────────────────────────────────
# GET /api/alerts/
# ─────────────────────────────────────────────────────────────────────

@_auth
def alerts_list(request):
    hours    = _parse_int(request.GET.get('hours', '24'), 24, 1, 720)
    severity = request.GET.get('severity', '')
    kind     = request.GET.get('kind', '')

    qs = Alert.objects.filter(
        triggered_at__gte=timezone.now() - timedelta(hours=hours),
    )
    if severity:
        qs = qs.filter(severity=severity)
    if kind:
        qs = qs.filter(kind=kind)

    rows = [
        {
            'id':            a.id,
            'triggered_at':  a.triggered_at.isoformat(),
            'kind':          a.kind,
            'severity':      a.severity,
            'title':         a.title,
            'message':       a.message,
            'metric_value':  a.metric_value,
            'threshold':     a.threshold,
            'acknowledged':  a.acknowledged,
            'channels':      a.notified_channels,
        }
        for a in qs[:500]
    ]
    return JsonResponse({'count': len(rows), 'window_hours': hours, 'alerts': rows})


@csrf_exempt
@_auth
@require_http_methods(['POST'])
def alert_ack(request, pk: int):
    alert = get_object_or_404(Alert, pk=pk)
    alert.acknowledged = True
    alert.resolved_at  = timezone.now()
    alert.save(update_fields=['acknowledged', 'resolved_at'])
    return JsonResponse({'status': 'ok', 'id': alert.id, 'acknowledged': True})


@_auth
def releases_list(request):
    days = _parse_int(request.GET.get('days', '30'), 30, 1, 365)
    qs = ReleaseEvent.objects.filter(
        occurred_at__gte=timezone.now() - timedelta(days=days),
    )
    rows = [
        {
            'id':              r.id,
            'occurred_at':     r.occurred_at.isoformat(),
            'event':           r.event,
            'version':         r.version,
            'previous_version':r.previous_version,
            'offline_score':   r.offline_score,
            'threshold':       r.threshold,
            'success':         r.success,
            'triggered_by':    r.triggered_by,
            'reason':          r.reason,
            'git_sha':         r.git_sha,
        }
        for r in qs[:500]
    ]
    return JsonResponse({'count': len(rows), 'window_days': days, 'releases': rows})


# ─────────────────────────────────────────────────────────────────────
# DEMO ENDPOINTS — pour la soutenance (boutons sur le dashboard)
# ─────────────────────────────────────────────────────────────────────

@csrf_exempt
@_auth
@require_http_methods(['POST'])
def demo_release_gate(request):
    """Déclenche une release gate de démo."""
    from .release import ReleaseService
    import random
    version = f"v{random.randint(1,9)}.{random.randint(0,9)}-demo"
    sha = ''.join(random.choices('abcdef0123456789', k=7))
    event = ReleaseService().decide(
        version=version, git_sha=sha, triggered_by='demo'
    )
    return JsonResponse({
        'status':   'ok',
        'event':    event.event,
        'version':  event.version,
        'score':    event.offline_score,
        'message':  f"Release Gate exécutée : {event.event.upper()}",
    })


@csrf_exempt
@_auth
@require_http_methods(['POST'])
def demo_rollback(request):
    """Déclenche un rollback de démo (en mode dry-run)."""
    from .release import ReleaseService
    event = ReleaseService().rollback(
        reason="Démo soutenance — rollback simulé",
        triggered_by='demo',
        dry_run=True,
    )
    return JsonResponse({
        'status':   'ok',
        'success':  event.success,
        'version':  event.version,
        'message':  f"Rollback {'réussi' if event.success else 'échoué'}",
    })


@csrf_exempt
@_auth
@require_http_methods(['POST'])
def demo_run_alerts(request):
    """Lance le moteur d'alertes de démo."""
    from .engine import AlertEngine
    alerts = AlertEngine().run(window_minutes=5)
    return JsonResponse({
        'status':   'ok',
        'count':    len(alerts),
        'message':  f"{len(alerts)} alerte(s) déclenchée(s)",
    })


@csrf_exempt
@_auth
@require_http_methods(['POST'])
def demo_reset(request):
    """Vide toutes les alertes et release events (pour démo propre)."""
    a_count = Alert.objects.count()
    r_count = ReleaseEvent.objects.count()
    Alert.objects.all().delete()
    ReleaseEvent.objects.all().delete()
    return JsonResponse({
        'status':  'ok',
        'message': f"{a_count} alertes et {r_count} releases supprimées",
    })


def _parse_int(value, default, lo, hi):
    try:
        return max(lo, min(hi, int(value)))
    except (TypeError, ValueError):
        return default