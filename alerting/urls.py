"""
Student #5 — Endpoints API pour l'alerting + démo.
"""

from django.urls import path

from . import views

app_name = 'alerting'

urlpatterns = [
    path('',                  views.alerts_list,    name='list'),
    path('<int:pk>/ack/',     views.alert_ack,      name='ack'),
    path('releases/',         views.releases_list,  name='releases'),

    # Démo — boutons du dashboard
    path('demo/release-gate/', views.demo_release_gate, name='demo-gate'),
    path('demo/rollback/',     views.demo_rollback,     name='demo-rollback'),
    path('demo/run-alerts/',   views.demo_run_alerts,   name='demo-alerts'),
    path('demo/reset/',        views.demo_reset,        name='demo-reset'),
]