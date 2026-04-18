"""
Student #3 — Online Monitoring Middleware

Intercepte chaque requête LLM en production et mesure :
- Latence (ms)
- Taux d'erreur (4xx/5xx)
- Token usage (depuis le body JSON de la réponse)
- Score de drift sémantique

Différence avec Student #2 :
  Student #2 → évalue offline sur un dataset fixe (BLEU/ROUGE/LLM-Judge)
  Student #3 → surveille online les vraies requêtes utilisateurs en temps réel
"""

import time
import json
import logging
import hashlib
import threading

from django.utils.deprecation import MiddlewareMixin
from django.conf import settings

logger = logging.getLogger("llm_monitor")

_local = threading.local()

# Chemins à surveiller, configurables dans settings.py
MONITORED_PREFIXES = getattr(settings, 'LLM_MONITOR_PATHS', ['/api/llm/', '/api/infer/'])


class LLMMonitoringMiddleware(MiddlewareMixin):
    """
    Middleware de monitoring online pour les endpoints LLM.

    Placé en haut du stack MIDDLEWARE dans settings.py pour capturer
    toutes les requêtes avant tout autre traitement.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        # Import lazy pour éviter les imports circulaires
        from .metrics_store import MetricsStore
        from .drift_detector import DriftDetector
        self.store = MetricsStore()
        self.drift = DriftDetector()

    def process_request(self, request):
        if not self._is_monitored(request.path):
            return None

        _local.start_ts  = time.perf_counter()
        _local.monitored = True
        _local.fingerprint = self._fingerprint(request)
        return None

    def process_response(self, request, response):
        if not getattr(_local, 'monitored', False):
            return response

        _local.monitored = False

        latency_ms  = (time.perf_counter() - _local.start_ts) * 1000
        is_error    = response.status_code >= 400
        tokens      = self._extract_tokens(response)
        drift_score = self.drift.score(_local.fingerprint)

        metric = {
            'path':               request.path,
            'method':             request.method,
            'status_code':        response.status_code,
            'latency_ms':         round(latency_ms, 2),
            'is_error':           is_error,
            'prompt_tokens':      tokens.get('prompt_tokens', 0),
            'completion_tokens':  tokens.get('completion_tokens', 0),
            'total_tokens':       tokens.get('total_tokens', 0),
            'drift_score':        round(drift_score, 4),
            'drift_alert':        drift_score > self.drift.ALERT_THRESHOLD,
        }

        self.store.record(metric)

        # Headers utiles pour le dashboard de Student #4
        response['X-LLM-Latency-Ms']  = str(metric['latency_ms'])
        response['X-LLM-Drift-Score'] = str(metric['drift_score'])

        log_level = logging.WARNING if (metric['drift_alert'] or is_error) else logging.INFO
        logger.log(log_level,
            "[Monitor] %s %s → %s | %.0fms | drift=%.3f | tokens=%s",
            request.method, request.path, response.status_code,
            latency_ms, drift_score, metric['total_tokens']
        )

        return response

    def process_exception(self, request, exception):
        if not getattr(_local, 'monitored', False):
            return None

        _local.monitored = False
        latency_ms = (time.perf_counter() - _local.start_ts) * 1000

        self.store.record({
            'path':              request.path,
            'method':            request.method,
            'status_code':       500,
            'latency_ms':        round(latency_ms, 2),
            'is_error':          True,
            'prompt_tokens':     0,
            'completion_tokens': 0,
            'total_tokens':      0,
            'drift_score':       0.0,
            'drift_alert':       False,
            'exception':         type(exception).__name__,
        })

        logger.error("[Monitor] Exception sur %s : %s", request.path, exception)
        return None

    # ------------------------------------------------------------------
    # Helpers privés
    # ------------------------------------------------------------------

    def _is_monitored(self, path: str) -> bool:
        return any(path.startswith(p) for p in MONITORED_PREFIXES)

    def _fingerprint(self, request) -> str:
        """Empreinte légère du prompt — ne stocke pas le texte brut (RGPD)."""
        try:
            body = request.body.decode('utf-8', errors='ignore')
            data = json.loads(body)
            text = data.get('prompt', data.get('messages', ''))
            if isinstance(text, list):
                text = ' '.join(m.get('content', '') for m in text)
            return hashlib.sha256(text.encode()).hexdigest()
        except Exception:
            return ''

    def _extract_tokens(self, response) -> dict:
        """Lit le token usage depuis le body JSON de la réponse LLM."""
        try:
            body  = json.loads(response.content.decode('utf-8', errors='ignore'))
            usage = body.get('usage', {})
            return {
                'prompt_tokens':     usage.get('prompt_tokens',     usage.get('input_tokens',  0)),
                'completion_tokens': usage.get('completion_tokens', usage.get('output_tokens', 0)),
                'total_tokens':      usage.get('total_tokens', 0),
            }
        except Exception:
            return {}