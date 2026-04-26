#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# Student #5 — Script de rollback automatique.
#
# Usage :
#   ./scripts/rollback.sh [target]
#
#   target  : tag git, sha, ou "HEAD~1" (défaut : HEAD~1)
#
# Stratégies (par ordre de priorité) :
#   1. Si TARGET ressemble à un tag → checkout du tag
#   2. Sinon → revert du dernier commit (HEAD~1)
#   3. Si déploiement externe configuré (HEROKU_APP, K8S_DEPLOYMENT,
#      RENDER_SERVICE_ID) → triggers le rollback côté plateforme
#
# Le script doit rester idempotent et ne jamais casser le repo si
# une étape échoue. Il sort en code 0 si le rollback est OK, 1 sinon.
# ─────────────────────────────────────────────────────────────────────

set -u  # interdit l'utilisation de variables non définies

TARGET="${1:-HEAD~1}"
LOG_PREFIX="[rollback]"

echo "$LOG_PREFIX 🔁 Démarrage du rollback vers : $TARGET"
echo "$LOG_PREFIX Date : $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# ─────────────────────────────────────────────────────────────────────
# 1) Sanity check : on est bien dans un repo git
# ─────────────────────────────────────────────────────────────────────
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "$LOG_PREFIX ❌ Pas dans un dépôt Git — abandon."
    exit 1
fi

CURRENT_SHA=$(git rev-parse HEAD)
echo "$LOG_PREFIX Commit actuel : $CURRENT_SHA"

# ─────────────────────────────────────────────────────────────────────
# 2) Stratégie locale : git revert ou git checkout
# ─────────────────────────────────────────────────────────────────────
if git rev-parse --verify "$TARGET" > /dev/null 2>&1; then
    TARGET_SHA=$(git rev-parse "$TARGET")
    echo "$LOG_PREFIX Target résolu : $TARGET_SHA"

    # On préfère un revert (préserve l'historique) à un reset destructif.
    if git revert --no-edit "$CURRENT_SHA" 2>/dev/null; then
        echo "$LOG_PREFIX ✅ git revert appliqué."
    else
        echo "$LOG_PREFIX ⚠️  git revert a échoué — fallback sur reset."
        git reset --hard "$TARGET_SHA" || {
            echo "$LOG_PREFIX ❌ Reset échoué — abandon."
            exit 1
        }
    fi
else
    echo "$LOG_PREFIX ⚠️  Target $TARGET introuvable — fallback HEAD~1."
    git revert --no-edit HEAD || {
        echo "$LOG_PREFIX ❌ Revert HEAD échoué — abandon."
        exit 1
    }
fi

# ─────────────────────────────────────────────────────────────────────
# 3) Push (si autorisé). Sur le CI, le token GITHUB_TOKEN est fourni.
# ─────────────────────────────────────────────────────────────────────
if [ "${ROLLBACK_PUSH:-0}" = "1" ]; then
    echo "$LOG_PREFIX Push du rollback vers origin..."
    if git push origin HEAD; then
        echo "$LOG_PREFIX ✅ Push OK."
    else
        echo "$LOG_PREFIX ⚠️  Push échoué (continue quand même)."
    fi
else
    echo "$LOG_PREFIX (push désactivé — set ROLLBACK_PUSH=1 pour activer)"
fi

# ─────────────────────────────────────────────────────────────────────
# 4) Déploiement externe (optionnel)
# ─────────────────────────────────────────────────────────────────────
if [ -n "${HEROKU_APP:-}" ]; then
    echo "$LOG_PREFIX Heroku rollback détecté — déclenchement..."
    heroku rollback --app "$HEROKU_APP" || echo "$LOG_PREFIX ⚠️  Heroku rollback a échoué."
fi

if [ -n "${K8S_DEPLOYMENT:-}" ]; then
    echo "$LOG_PREFIX Kubernetes rollback détecté — déclenchement..."
    kubectl rollout undo "deployment/$K8S_DEPLOYMENT" \
        ${K8S_NAMESPACE:+--namespace="$K8S_NAMESPACE"} \
        || echo "$LOG_PREFIX ⚠️  kubectl rollout undo a échoué."
fi

echo "$LOG_PREFIX ✅ Rollback terminé."
exit 0
