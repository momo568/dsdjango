from django.apps import AppConfig

class LlmMonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name               = 'llm_monitor'
    verbose_name       = 'LLM Online Monitor'