import json
from django.core.management.base import BaseCommand
from llm_monitor.models import InferenceMetric

class Command(BaseCommand):
    help = "Exporte les requêtes ayant déclenché une alerte de Drift pour l'Étudiant 2"

    def handle(self, *args, **options):
        # On récupère toutes les requêtes en alerte de drift
        drifted_metrics = InferenceMetric.objects.filter(drift_alert=True).order_by('-recorded_at')
        
        count = drifted_metrics.count()
        if count == 0:
            self.stdout.write(self.style.WARNING("Aucun drift détecté dans la base de données."))
            return

        # Dans un vrai projet, le fingerprint serait décodé ou on stockerait les prompts bruts
        # Ici, pour la simulation, on va exporter les données disponibles
        export_data = []
        for m in drifted_metrics:
            export_data.append({
                "recorded_at": m.recorded_at.isoformat(),
                "path": m.path,
                "latency_ms": m.latency_ms,
                "drift_score": m.drift_score,
                "prompt_a_traiter": "Question hors-sujet interceptée en production" 
            })

        output_file = "nouveau_dataset_drift.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=4, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(f"✅ {count} requêtes en dérive (Drift) exportées !"))
        self.stdout.write(self.style.SUCCESS(f"📁 Fichier généré : {output_file}"))
        self.stdout.write(self.style.SUCCESS("👉 Étudiant 3 : Envoie ce fichier à l'Étudiant 2 !"))
        self.stdout.write(self.style.SUCCESS("👉 Étudiant 2 : Ajoute ces cas à ton 'dataset_hack.json' et relance l'évaluation."))
