"""
Student #5 — `python manage.py run_alerts`

Évalue les règles d'alerting et envoie les notifications.
À utiliser via cron ou GitHub Actions toutes les 1-5 minutes.
"""

from django.core.management.base import BaseCommand

from alerting.engine import AlertEngine


class Command(BaseCommand):
    help = "Évalue les règles d'alerting et déclenche les notifications."

    def add_arguments(self, parser):
        parser.add_argument(
            '--window', type=int, default=5,
            help='Fenêtre d\'analyse en minutes (défaut : 5)',
        )

    def handle(self, *args, **options):
        window = options['window']
        self.stdout.write(self.style.NOTICE(
            f"\n🔍 [run_alerts] Évaluation des règles sur les {window} dernières minutes..."
        ))

        alerts = AlertEngine().run(window_minutes=window)

        if not alerts:
            self.stdout.write(self.style.SUCCESS(
                "✅ Aucune alerte déclenchée — système healthy."
            ))
            return

        self.stdout.write(self.style.WARNING(
            f"\n⚠️  {len(alerts)} alerte(s) déclenchée(s) :"
        ))
        for a in alerts:
            self.stdout.write(f"   • [{a.severity.upper()}] {a.title}")
        self.stdout.write('')
