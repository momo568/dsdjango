"""
Student #5 — `python manage.py rollback`

Déclenche un rollback (manuel ou auto).

Manuel :
    python manage.py rollback --reason "Régression détectée par QA"

Auto (vérifie la santé d'abord) :
    python manage.py rollback --auto

Dry-run (simulation, pas d'exécution réelle) :
    python manage.py rollback --auto --dry-run
"""

import sys

from django.core.management.base import BaseCommand

from alerting.release import ReleaseService


class Command(BaseCommand):
    help = "Déclenche un rollback de la dernière release (manuel ou automatique)."

    def add_arguments(self, parser):
        parser.add_argument('--auto', action='store_true',
                            help="Ne rollback que si la santé est critique")
        parser.add_argument('--reason', type=str, default='',
                            help="Raison du rollback (obligatoire si manuel)")
        parser.add_argument('--window', type=int, default=10,
                            help="Fenêtre d'analyse pour --auto (minutes)")
        parser.add_argument('--dry-run', action='store_true',
                            help="Simulation : trace l'event mais n'exécute pas le script")

    def handle(self, *args, **options):
        service = ReleaseService()

        if options['auto']:
            self.stdout.write(self.style.NOTICE(
                f"\n🔁 [rollback --auto] Vérification de la santé "
                f"sur les {options['window']} dernières minutes..."
            ))
            event = service.auto_rollback_if_unhealthy(
                window_minutes=options['window'],
                dry_run=options['dry_run'],
            )
            if event is None:
                self.stdout.write(self.style.SUCCESS(
                    "✅ Santé OK — pas de rollback nécessaire.\n"
                ))
                sys.exit(0)
        else:
            if not options['reason']:
                self.stdout.write(self.style.ERROR(
                    "❌ --reason est obligatoire pour un rollback manuel."
                ))
                sys.exit(2)
            self.stdout.write(self.style.NOTICE("\n🔁 [rollback] Rollback manuel..."))
            event = service.rollback(
                reason=options['reason'],
                triggered_by='manual',
                dry_run=options['dry_run'],
            )

        # Reporting
        target = event.version or 'HEAD~1'
        prefix = '' if target.startswith('v') else 'v'
        if event.success:
            self.stdout.write(self.style.SUCCESS(f"\n✅ Rollback réussi → {prefix}{target}"))
            sys.exit(0)
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ Rollback échoué : {event.reason}"))
            sys.exit(1)
