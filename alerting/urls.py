"""
 Endpoints API pour l'alerting.

GET  /api/alerts/         → liste des alertes récentes
POST /api/alerts/{id}/ack/ → acquittement
GET  /api/alerts/releases/ → historique des releases & rollbacks
"""

from django.urls import path

from . import views

app_name = 'alerting'

urlpatterns = [
    path('',                  views.alerts_list,    name='list'),
    path('<int:pk>/ack/',     views.alert_ack,      name='ack'),
    path('releases/',         views.releases_list,  name='releases'),
]
