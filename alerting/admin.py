from django.contrib import admin

from .models import Alert, AlertChannel, ReleaseEvent


@admin.register(AlertChannel)
class AlertChannelAdmin(admin.ModelAdmin):
    list_display  = ('name', 'kind', 'enabled', 'min_severity', 'created_at')
    list_filter   = ('kind', 'enabled', 'min_severity')
    search_fields = ('name', 'target')


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display  = ('triggered_at', 'severity', 'kind', 'title', 'acknowledged', 'notified_channels')
    list_filter   = ('severity', 'kind', 'acknowledged')
    search_fields = ('title', 'message')
    readonly_fields = ('triggered_at',)
    actions       = ['acknowledge_selected']

    @admin.action(description="Marquer comme acquittées")
    def acknowledge_selected(self, request, queryset):
        queryset.update(acknowledged=True)


@admin.register(ReleaseEvent)
class ReleaseEventAdmin(admin.ModelAdmin):
    list_display  = ('occurred_at', 'event', 'version', 'success', 'offline_score', 'triggered_by')
    list_filter   = ('event', 'success', 'triggered_by')
    search_fields = ('version', 'git_sha', 'reason')
    readonly_fields = ('occurred_at',)
