from django.db import migrations, models


class Migration(migrations.Migration):
    initial      = True
    dependencies  = []

    operations = [
        migrations.CreateModel(
            name='InferenceMetric',
            fields=[
                ('id',                models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('recorded_at',       models.DateTimeField(auto_now_add=True, db_index=True)),
                ('path',              models.CharField(db_index=True, max_length=255)),
                ('method',            models.CharField(default='POST', max_length=10)),
                ('status_code',       models.PositiveSmallIntegerField(default=200)),
                ('latency_ms',        models.FloatField()),
                ('is_error',          models.BooleanField(db_index=True, default=False)),
                ('exception',         models.CharField(blank=True, default='', max_length=128)),
                ('prompt_tokens',     models.PositiveIntegerField(default=0)),
                ('completion_tokens', models.PositiveIntegerField(default=0)),
                ('total_tokens',      models.PositiveIntegerField(default=0)),
                ('drift_score',       models.FloatField(default=0.0)),
                ('drift_alert',       models.BooleanField(db_index=True, default=False)),
            ],
            options={'ordering': ['-recorded_at'], 'verbose_name': 'Inference Metric', 'verbose_name_plural': 'Inference Metrics'},
        ),
        migrations.AddIndex(model_name='inferencemetric', index=models.Index(fields=['recorded_at', 'is_error'],   name='mon_rec_err_idx')),
        migrations.AddIndex(model_name='inferencemetric', index=models.Index(fields=['recorded_at', 'drift_alert'],name='mon_rec_drift_idx')),
        migrations.AddIndex(model_name='inferencemetric', index=models.Index(fields=['path', 'recorded_at'],       name='mon_path_rec_idx')),
    ]