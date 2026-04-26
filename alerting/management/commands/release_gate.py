"""
Student #5 — `python manage.py release_gate`

Lit eval_results.json et décide DEPLOY/BLOCK.
Code de sortie :
  0 → DEPLOY autorisé
  1 → release BLOQUÉE (CI doit s'arrêter)

Utilisé par GitHub Actions :
    python manage.py release_gate --version $VERSION --git-sha $GITHUB_SHA
"""

import sys

from django.core.management.base import BaseCommand

from alerting.release import ReleaseService


class Command(BaseCommand):
    help = "Décide DEPLOY/BLOCK selon eval_results.json. Trace l'événement."

    def add_arguments(self, parser):
        # Note : Django utilise déjà --version, on passe par --release-version
        parser.add_argument('--release-version', dest='release_version',
                            type=str, default='', help='Version à déployer')
        parser.add_argument('--git-sha', dest='git_sha',
                            type=str, default='', help='SHA du commit')
        parser.add_argument('--triggered-by', dest='triggered_by',
                            type=str, default='ci',
                            help="Déclencheur (ci/manual/auto)")

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("\n🚦 [release_gate] Évaluation de la porte de release..."))

        event = ReleaseService().decide(
            version=options['release_version'],
            git_sha=options['git_sha'],
            triggered_by=options['triggered_by'],
        )

        self.stdout.write(f"  Score offline : {event.offline_score}")
        self.stdout.write(f"  Seuil         : {event.threshold}")
        self.stdout.write(f"  Décision      : {event.event.upper()}")
        self.stdout.write(f"  Raison        : {event.reason}")

        if event.event == 'deploy':
            self.stdout.write(self.style.SUCCESS("\n✅ RELEASE AUTORISÉE\n"))
            sys.exit(0)
        else:
            self.stdout.write(self.style.ERROR("\n❌ RELEASE BLOQUÉE\n"))
            sys.exit(1)
