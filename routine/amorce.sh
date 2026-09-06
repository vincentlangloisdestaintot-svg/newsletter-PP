#!/usr/bin/env bash
# Amorçage de la routine quotidienne.
#
# Exécuté au début de chaque tâche planifiée, dans une session vierge. Récupère
# le code, installe les dépendances et lance la collecte de données.
#
# Variables attendues dans l'environnement, fournies par le prompt de la tâche :
#   GH_TOKEN         jeton GitHub à portée lecture seule sur le seul dépôt
#   GH_DEPOT         propriétaire/nom, ex. vincent/veille-patrimoniale
#   RESEND_API_KEY   clé d'envoi
#   VEILLE_*         destinataire, expéditeur, canal
#
# Ce script ne contient aucun secret : il les lit dans l'environnement.

set -uo pipefail

RACINE="${RACINE:-$HOME/veille}"
JOURNAL="${RACINE}/amorce.log"

echo "=== Amorçage $(TZ='Europe/Paris' date '+%Y-%m-%d %H:%M %Z') ==="

# --- 1. Code ---------------------------------------------------------------
if [ -d "${RACINE}/.git" ]; then
  echo "Dépôt déjà présent, mise à jour."
  git -C "${RACINE}" fetch --quiet origin && \
  git -C "${RACINE}" reset --hard --quiet origin/HEAD
else
  echo "Clonage du dépôt."
  rm -rf "${RACINE}"
  git clone --quiet --depth 50 \
    "https://x-access-token:${GH_TOKEN}@github.com/${GH_DEPOT}.git" "${RACINE}" \
    || { echo "ÉCHEC : clonage impossible. Vérifier GH_TOKEN et GH_DEPOT."; exit 10; }
fi

cd "${RACINE}" || exit 11

# L'URL distante contient le jeton : on la neutralise dans la config locale
# pour qu'il n'apparaisse pas dans un éventuel affichage de configuration.
git config --local --unset-all remote.origin.url >/dev/null 2>&1 || true
git config --local remote.origin.url "https://github.com/${GH_DEPOT}.git"

# --- 2. Dépendances --------------------------------------------------------
echo "Installation des dépendances."
pip install --quiet --break-system-packages -r requirements.txt 2>&1 | tail -3

# --- 3. Collecte -----------------------------------------------------------
echo "Collecte des données de marché."
python3 -m veille.main collecte --dossier travail -v 2>&1 | tee -a "${JOURNAL}" | tail -25

if [ ! -f travail/instruction.md ]; then
  echo "ÉCHEC : la collecte n'a pas produit travail/instruction.md."
  exit 12
fi

echo
echo "=== Amorçage terminé ==="
echo "Dossier de travail : ${RACINE}/travail"
echo "Fichiers prêts : instruction.md, donnees.json, schema.json"
