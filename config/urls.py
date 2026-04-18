from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # ✅ Student #3 — Endpoints de monitoring online
    # Utilisés par Student #4 (dashboard) et Student #5 (alertes + CI)
    path('api/monitor/', include('llm_monitor.urls')),
]