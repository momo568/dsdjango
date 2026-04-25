from django.urls import path
from . import views

urlpatterns = [
    path('',              views.index,            name='dashboard-index'),
    path('offline/',      views.offline_view,     name='dashboard-offline'),
    path('online/',       views.online_view,       name='dashboard-online'),
    path('versions/',     views.versions_view,     name='dashboard-versions'),
    path('health/',       views.health_view,       name='dashboard-health'),
    path('api/summary/',  views.api_summary,       name='api-summary'),
    path('comparaison/',  views.comparaison_view,  name='dashboard-comparaison'),
]