"""
Student #5 — Adapters de notification.

Chaque adapter implémente .send(alert) et retourne True si OK, False sinon.
On ne lève jamais d'exception : une erreur de notif ne doit pas casser l'app.
"""

import json
import logging
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from typing import Protocol

from django.conf import settings

logger = logging.getLogger('alerting')


SEVERITY_EMOJI = {
    'info':     'ℹ️',
    'warning':  '⚠️',
    'critical': '🚨',
}

SEVERITY_RANK = {'info': 0, 'warning': 1, 'critical': 2}


class Notifier(Protocol):
    def send(self, alert) -> bool: ...


# ─────────────────────────────────────────────────────────────────────
# Console (toujours dispo — fallback)
# ─────────────────────────────────────────────────────────────────────

class ConsoleNotifier:
    """Logge l'alerte dans la console / le fichier de log Django."""

    def __init__(self, target: str = ''):
        self.target = target

    def send(self, alert) -> bool:
        emoji = SEVERITY_EMOJI.get(alert.severity, '•')
        line  = (
            f"{emoji} [ALERT/{alert.severity.upper()}] {alert.title}\n"
            f"   kind     : {alert.kind}\n"
            f"   message  : {alert.message}\n"
            f"   value    : {alert.metric_value}  (seuil={alert.threshold})\n"
            f"   at       : {alert.triggered_at:%Y-%m-%d %H:%M:%S}"
        )
        if alert.severity == 'critical':
            logger.error(line)
        elif alert.severity == 'warning':
            logger.warning(line)
        else:
            logger.info(line)
        # Affichage console aussi pour les démos en cours
        print(line, flush=True)
        return True


# ─────────────────────────────────────────────────────────────────────
# Slack via Incoming Webhook
# ─────────────────────────────────────────────────────────────────────

class SlackNotifier:
    """Envoie l'alerte sur un Slack Incoming Webhook."""

    def __init__(self, target: str):
        self.webhook_url = target

    def send(self, alert) -> bool:
        if not self.webhook_url:
            logger.warning('[Slack] Pas d\'URL webhook configurée')
            return False

        emoji = SEVERITY_EMOJI.get(alert.severity, '•')
        color = {
            'info':     '#3498db',
            'warning':  '#f39c12',
            'critical': '#e74c3c',
        }.get(alert.severity, '#95a5a6')

        payload = {
            'text': f"{emoji} *Alerte LLM — {alert.severity.upper()}*",
            'attachments': [{
                'color': color,
                'title': alert.title,
                'text':  alert.message,
                'fields': [
                    {'title': 'Type',        'value': alert.kind,            'short': True},
                    {'title': 'Sévérité',    'value': alert.severity,        'short': True},
                    {'title': 'Valeur',      'value': str(alert.metric_value), 'short': True},
                    {'title': 'Seuil',       'value': str(alert.threshold),    'short': True},
                    {'title': 'Déclenchée',  'value': alert.triggered_at.strftime('%Y-%m-%d %H:%M:%S UTC'), 'short': False},
                ],
                'footer': 'LLM Monitoring — Student #5',
            }]
        }

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if 200 <= resp.status < 300:
                    return True
                logger.warning('[Slack] HTTP %s', resp.status)
                return False
        except urllib.error.URLError as e:
            logger.warning('[Slack] Échec envoi : %s', e)
            return False
        except Exception:
            logger.exception('[Slack] Exception inattendue')
            return False


# ─────────────────────────────────────────────────────────────────────
# Email via SMTP
# ─────────────────────────────────────────────────────────────────────

class EmailNotifier:
    """Envoie l'alerte par email à une liste de destinataires (séparés par virgule)."""

    def __init__(self, target: str):
        self.recipients = [t.strip() for t in target.split(',') if t.strip()]

    def send(self, alert) -> bool:
        if not self.recipients:
            logger.warning('[Email] Aucun destinataire configuré')
            return False

        host     = getattr(settings, 'EMAIL_HOST',     'localhost')
        port     = getattr(settings, 'EMAIL_PORT',     25)
        user     = getattr(settings, 'EMAIL_HOST_USER',     '')
        password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
        use_tls  = getattr(settings, 'EMAIL_USE_TLS', False)
        from_addr= getattr(settings, 'DEFAULT_FROM_EMAIL', 'llm-monitor@localhost')

        emoji   = SEVERITY_EMOJI.get(alert.severity, '•')
        subject = f"{emoji} [LLM-Monitor/{alert.severity.upper()}] {alert.title}"
        body    = (
            f"Alerte LLM Monitoring\n"
            f"========================\n\n"
            f"Type        : {alert.kind}\n"
            f"Sévérité    : {alert.severity}\n"
            f"Titre       : {alert.title}\n"
            f"Déclenchée  : {alert.triggered_at:%Y-%m-%d %H:%M:%S UTC}\n"
            f"Valeur      : {alert.metric_value}\n"
            f"Seuil       : {alert.threshold}\n\n"
            f"Détail :\n{alert.message}\n"
        )
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['Subject'] = subject
        msg['From']    = from_addr
        msg['To']      = ', '.join(self.recipients)

        try:
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                if use_tls:
                    smtp.starttls()
                if user and password:
                    smtp.login(user, password)
                smtp.send_message(msg)
            return True
        except Exception:
            logger.exception('[Email] Échec envoi')
            return False


# ─────────────────────────────────────────────────────────────────────
# Factory
# ─────────────────────────────────────────────────────────────────────

def build_notifier(channel) -> Notifier:
    """Construit le bon adapter à partir du modèle AlertChannel."""
    kind = (channel.kind or 'console').lower()
    if kind == 'slack':
        return SlackNotifier(channel.target)
    if kind == 'email':
        return EmailNotifier(channel.target)
    return ConsoleNotifier(channel.target)


def severity_at_least(actual: str, minimum: str) -> bool:
    """True si actual >= minimum (en termes de sévérité)."""
    return SEVERITY_RANK.get(actual, 0) >= SEVERITY_RANK.get(minimum, 0)
