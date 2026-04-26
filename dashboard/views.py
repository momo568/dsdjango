"""
Phase 4 — Dashboard de reporting
Étudiant 4 : visualisation des données des étudiants 1, 2 et 3
"""
import json
from pathlib import Path
from django.shortcuts import render
from django.http import JsonResponse
from django.conf import settings
from llm_monitor.metrics_store import MetricsStore

store = MetricsStore()
BASE  = Path(settings.BASE_DIR)

def _load_json(filename):
    path = BASE / filename
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def _health_badge(health):
    return {
        'healthy':  ('health-ok',       '●', 'OPÉRATIONNEL'),
        'degraded': ('health-degraded', '◆', 'DÉGRADÉ'),
        'critical': ('health-critical', '■', 'CRITIQUE'),
    }.get(health, ('health-unknown', '?', 'INCONNU'))

def index(request):
    summary  = store.summary(minutes=60)
    offline  = _load_json('eval_results.json')
    rapport  = _load_json('rapport_general.json')
    health   = summary.get('health', 'unknown')
    badge    = _health_badge(health)
    return render(request, 'dashboard/index.html', {
        'summary': summary, 'offline': offline,
        'rapport': rapport, 'health': health, 'badge': badge,
    })

def offline_view(request):
    offline    = _load_json('eval_results.json')
    comparison = _load_json('comparison_results.json')
    rapport    = _load_json('rapport_general.json')
    solutions_data = []
    if rapport.get('results'):
        for dataset_name, scores in rapport['results'].items():
            for solution_name, score in scores.items():
                solutions_data.append({'dataset': dataset_name, 'solution': solution_name, 'score': score})
    return render(request, 'dashboard/offline.html', {
        'offline': offline, 'comparison': comparison,
        'rapport': rapport, 'solutions_data': solutions_data,
    })

def online_view(request):
    minutes = int(request.GET.get('minutes', 60))
    summary = store.summary(minutes=minutes)
    recent  = list(store.recent(minutes=10)[:25])
    health  = summary.get('health', 'unknown')
    badge   = _health_badge(health)
    return render(request, 'dashboard/online.html', {
        'summary': summary, 'recent': recent,
        'minutes': minutes, 'health': health, 'badge': badge,
    })

def versions_view(request):
    comparison = _load_json('comparison_results.json')
    prompt_results = []
    model_results  = []
    if comparison.get('prompt_comparison', {}).get('results'):
        prompt_results = sorted(comparison['prompt_comparison']['results'], key=lambda x: x.get('average_score', 0), reverse=True)
    if comparison.get('model_comparison', {}).get('results'):
        model_results = sorted(comparison['model_comparison']['results'], key=lambda x: x.get('average_score', 0), reverse=True)
    return render(request, 'dashboard/versions.html', {
        'comparison': comparison, 'prompt_results': prompt_results, 'model_results': model_results,
    })

def health_view(request):
    summary = store.summary(minutes=5)
    health  = summary.get('health', 'unknown')
    badge   = _health_badge(health)
    offline = _load_json('eval_results.json')
    return render(request, 'dashboard/health.html', {
        'summary': summary, 'health': health, 'badge': badge, 'offline': offline,
    })

def api_summary(request):
    minutes = int(request.GET.get('minutes', 60))
    data    = store.summary(minutes=minutes)
    
    # Séries temporelles
    latency_qs = store.latency_timeseries(minutes=minutes)
    drift_qs   = store.drift_timeseries(minutes=minutes)
    data['latency_series'] = [{'x': r['bucket'].isoformat(), 'y': round(r['avg_latency'], 1)} for r in latency_qs]
    data['drift_series']   = [{'x': r['bucket'].isoformat(), 'y': round(r['avg_drift'], 4)} for r in drift_qs]
    
    # Offline scores depuis eval_results.json
    offline = _load_json('eval_results.json')
    data['offline_bleu']     = offline.get('bleu_score', 0)
    data['offline_rouge']    = offline.get('rouge_score', 0)
    data['offline_judge']    = offline.get('llm_judge_score', 0)
    data['offline_security'] = offline.get('security_score', 0)
    data['offline_avg']      = offline.get('average_score', 0)
    
    # Rapport général
    rapport = _load_json('rapport_general.json')
    if rapport.get('results'):
        data['rapport_results'] = rapport['results']
    
    return JsonResponse(data)


def comparaison_view(request):
    """Vue Avant/Après — créée par Oumaima (Étudiant 2) pour montrer l'amélioration du pipeline."""
    v1 = _load_json('eval_results_v1_before_nltk.json')  # Ancien (sans NLTK)
    v2 = _load_json('eval_results.json')                 # Nouveau (avec NLTK)

    metriques = [
        {'nom': 'BLEU',      'avant': v1.get('bleu_score', 0),      'apres': v2.get('bleu_score', 0)},
        {'nom': 'ROUGE',     'avant': v1.get('rouge_score', 0),     'apres': v2.get('rouge_score', 0)},
        {'nom': 'LLM-Judge', 'avant': v1.get('llm_judge_score', 0), 'apres': v2.get('llm_judge_score', 0)},
        {'nom': 'Sécurité',  'avant': v1.get('security_score', 0),  'apres': v2.get('security_score', 0)},
        {'nom': 'Moyenne',   'avant': v1.get('average_score', 0),   'apres': v2.get('average_score', 0)},
    ]

    # Load the 5 solutions
    solutions = []
    for i in range(1, 6):
        res = _load_json(f'results_solution{i}.json')
        if res:
            if 'winner_score' in res and 'results' in res:
                score = res.get('winner_score', 0)
                winner = res.get('winner', '')
                winner_data = next((r for r in res['results'] if r.get('prompt_name') == winner), {})
                metrics = [
                    winner_data.get('bleu_score', 0),
                    winner_data.get('rouge_score', 0),
                    winner_data.get('llm_judge_score', 0),
                    winner_data.get('security_score', 0)
                ]
                decision = 'DEPLOY' if winner_data.get('passed') else 'BLOCK'
            else:
                score = res.get('average_score', 0)
                metrics = [
                    res.get('bleu_score', 0),
                    res.get('rouge_score', 0),
                    res.get('llm_judge_score', 0),
                    res.get('security_score', 0)
                ]
                decision = res.get('decision', 'N/A')

            solutions.append({
                'id': i,
                'name': f'Solution {i}',
                'score': score,
                'metrics': metrics,
                'decision': decision
            })

    return render(request, 'dashboard/comparaison.html', {
        'v1': v1,
        'v2': v2,
        'metriques': metriques,
        'solutions': solutions,
    })


def alerts_view(request):
    """Page Alertes & Releases (Student #5)."""
    return render(request, 'dashboard/alerts.html', {
        'api_key': getattr(settings, 'LLM_MONITOR_API_KEY', 'dev-key'),
    })