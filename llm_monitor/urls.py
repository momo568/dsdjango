from django.urls import path
from . import views

app_name = 'llm_monitor'

urlpatterns = [
    path('summary/',      views.summary_view,     name='summary'),
    path('timeseries/',   views.timeseries_view,  name='timeseries'),
    path('recent/',       views.recent_view,       name='recent'),
    path('health/',       views.health_view,       name='health'),
    path('drift/reset/',  views.drift_reset_view,  name='drift-reset'),
]