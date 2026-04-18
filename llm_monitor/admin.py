from django.contrib import admin
from django.utils.html import format_html
from .models import InferenceMetric


@admin.register(InferenceMetric)
class InferenceMetricAdmin(admin.ModelAdmin):
    list_display  = ('recorded_at', 'path', 'status_badge', 'latency_ms', 'total_tokens', 'drift_badge')
    list_filter   = ('is_error', 'drift_alert', 'path')
    readonly_fields = [f.name for f in InferenceMetric._meta.fields]
    date_hierarchy = 'recorded_at'
    ordering      = ('-recorded_at',)

    def status_badge(self, obj):
        color = '#22c55e' if obj.status_code < 400 else ('#f59e0b' if obj.status_code < 500 else '#ef4444')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px">{}</span>', color, obj.status_code)
    status_badge.short_description = 'Status'

    def drift_badge(self, obj):
        color = '#ef4444' if obj.drift_alert else ('#22c55e' if obj.drift_score < 0.2 else '#f59e0b')
        return format_html('<span style="background:{};color:#fff;padding:2px 8px;border-radius:4px">{:.3f}</span>', color, obj.drift_score)
    drift_badge.short_description = 'Drift'

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False