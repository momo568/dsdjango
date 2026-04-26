# Generated migration for alerting app 

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='AlertChannel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100, unique=True)),
                ('kind', models.CharField(
                    choices=[('console', 'Console / Logs'), ('slack', 'Slack Webhook'), ('email', 'Email SMTP')],
                    default='console', max_length=16)),
                ('enabled', models.BooleanField(default=True)),
                ('target', models.CharField(blank=True, default='', max_length=500)),
                ('min_severity', models.CharField(
                    choices=[('info', 'info'), ('warning', 'warning'), ('critical', 'critical')],
                    default='warning', max_length=16)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'verbose_name': 'Alert Channel', 'verbose_name_plural': 'Alert Channels'},
        ),
        migrations.CreateModel(
            name='Alert',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('triggered_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('kind', models.CharField(
                    choices=[
                        ('error_rate', "Taux d'erreur"),
                        ('latency', 'Latence élevée'),
                        ('drift', 'Drift sémantique'),
                        ('release_gate', 'Release gate échouée'),
                        ('rollback', 'Rollback déclenché'),
                        ('health', 'Health check'),
                    ],
                    db_index=True, max_length=32)),
                ('severity', models.CharField(
                    choices=[('info', 'Info'), ('warning', 'Warning'), ('critical', 'Critical')],
                    db_index=True, default='warning', max_length=16)),
                ('title', models.CharField(max_length=200)),
                ('message', models.TextField()),
                ('metric_value', models.FloatField(blank=True, null=True)),
                ('threshold', models.FloatField(blank=True, null=True)),
                ('acknowledged', models.BooleanField(db_index=True, default=False)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('notified_channels', models.CharField(blank=True, default='', max_length=255)),
            ],
            options={
                'ordering': ['-triggered_at'],
                'verbose_name': 'Alert',
                'verbose_name_plural': 'Alerts',
                'indexes': [
                    models.Index(fields=['triggered_at', 'severity'], name='alerting_al_trigger_severity_idx'),
                    models.Index(fields=['kind', 'triggered_at'], name='alerting_al_kind_trigger_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='ReleaseEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ('occurred_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('event', models.CharField(
                    choices=[('deploy', 'Déploiement'), ('rollback', 'Rollback'), ('blocked', 'Release bloquée')],
                    db_index=True, max_length=16)),
                ('version', models.CharField(blank=True, default='', max_length=64)),
                ('previous_version', models.CharField(blank=True, default='', max_length=64)),
                ('offline_score', models.FloatField(blank=True, null=True)),
                ('threshold', models.FloatField(blank=True, null=True)),
                ('triggered_by', models.CharField(blank=True, default='ci', max_length=64)),
                ('reason', models.TextField(blank=True, default='')),
                ('success', models.BooleanField(default=True)),
                ('git_sha', models.CharField(blank=True, default='', max_length=40)),
            ],
            options={
                'ordering': ['-occurred_at'],
                'verbose_name': 'Release Event',
                'verbose_name_plural': 'Release Events',
            },
        ),
    ]
