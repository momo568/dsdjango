"""
python manage.py seed_metrics --count 300 --drift-spike --error-burst

Génère des données synthétiques pour permettre à Student #4 (dashboard)
et Student #5 (alertes) de travailler sans attendre un LLM réel.
"""

import random
import math
from datetime import datetime, timezone, timedelta
from django.core.management.base import BaseCommand
from llm_monitor.models import InferenceMetric


class Command(BaseCommand):
    help = 'Génère des InferenceMetric synthétiques pour les tests'

    def add_arguments(self, parser):
        parser.add_argument('--count',       type=int, default=200)
        parser.add_argument('--drift-spike', action='store_true', help='Simule un spike de drift sur les 30 dernières lignes')
        parser.add_argument('--error-burst', action='store_true', help='Simule une rafale d\'erreurs en milieu de série')

    def handle(self, *args, **options):
        count       = options['count']
        drift_spike = options['drift_spike']
        error_burst = options['error_burst']
        paths       = ['/api/llm/chat/', '/api/llm/summarize/', '/api/infer/']
        now         = datetime.now(timezone.utc)

        rows = []
        for i in range(count):
            ts         = now - timedelta(minutes=count - i)
            latency    = max(80, 600 + 400 * math.sin(i / 20) + random.gauss(0, 150))
            drift      = random.uniform(0.35, 0.65) if (drift_spike and i >= count - 30) else random.uniform(0.0, 0.25)
            is_error   = (error_burst and 50 <= i <= 70) or random.random() < 0.04
            status     = random.choice([500, 502]) if is_error else 200

            rows.append(InferenceMetric(
                recorded_at       = ts,
                path              = random.choice(paths),
                method            = 'POST',
                status_code       = status,
                latency_ms        = round(latency, 2),
                is_error          = is_error,
                prompt_tokens     = random.randint(50, 600),
                completion_tokens = random.randint(20, 400),
                total_tokens      = random.randint(70, 1000),
                drift_score       = round(drift, 4),
                drift_alert       = drift > 0.35,
            ))

        InferenceMetric.objects.bulk_create(rows)
        self.stdout.write(self.style.SUCCESS(
            f'✓ {count} métriques créées'
            + (' + drift spike' if drift_spike else '')
            + (' + error burst' if error_burst else '')
        ))