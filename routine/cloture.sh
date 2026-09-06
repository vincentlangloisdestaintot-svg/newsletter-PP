#!/usr/bin/env bash
# Clôture de la routine quotidienne : contrôle, rendus, archive.
#
# L'envoi de l'email n'est PAS fait ici : il est fait par la session elle-même
# avec le connecteur Gmail, à partir des fichiers produits par ce script. C'est
# ce qui évite d'avoir à stocker une clé d'envoi.
#
# Ce script produit dans travail/ :
#   apercu.html                        corps du mail, prêt à envoyer
#   apercu.md                          version texte
#   Veille_patrimoniale_AAAA-MM-JJ.pdf pièce jointe
#   piece_jointe.b64                   le même PDF encodé, prêt à joindre
#   sujet.txt                          la ligne d'objet
#
# Variables attendues :
#   GH_TOKEN, GH_DEPOT   pour pousser l'archive
#   RACINE               racine du dépôt cloné

set -uo pipefail

RACINE="${RACINE:-$HOME/veille}"
cd "${RACINE}" || exit 11

if [ ! -f travail/brief.json ]; then
  echo "ÉCHEC : travail/brief.json absent. Rien à livrer."
  exit 20
fi

# --- 1. Contrôle, rendus, archive ------------------------------------------
# VEILLE_CANAL=aucun : le script ne tente aucun envoi, il produit les rendus.
echo "Contrôle et rendus."
VEILLE_CANAL=aucun python3 -m veille.main finalise \
  --dossier travail --sans-envoi -v 2>&1 | tail -30

JOUR=$(TZ='Europe/Paris' date +%Y-%m-%d)
PDF="travail/Veille_patrimoniale_${JOUR}.pdf"

if [ ! -f travail/apercu.html ]; then
  echo "ÉCHEC : le corps du mail n'a pas été produit."
  exit 21
fi

# --- 2. Objet du mail -------------------------------------------------------
TITRE=$(python3 -c "
import datetime, sys
sys.path.insert(0, '.')
from veille import dates_fr
print(dates_fr.titre(dates_fr.aujourdhui_paris()).title())
" 2>/dev/null || echo "${JOUR}")

if grep -qi "contrôle.*bloquant" travail/apercu.html; then
  echo "Veille patrimoniale — ${TITRE} ⚠" > travail/sujet.txt
else
  echo "Veille patrimoniale — ${TITRE}" > travail/sujet.txt
fi

# --- 3. Pièce jointe encodée ------------------------------------------------
if [ -f "${PDF}" ]; then
  base64 -w0 "${PDF}" > travail/piece_jointe.b64 2>/dev/null \
    || base64 -i "${PDF}" | tr -d '\n' > travail/piece_jointe.b64
  TAILLE=$(wc -c < travail/piece_jointe.b64)
  echo "Pièce jointe prête : ${PDF} (${TAILLE} octets encodés)."
else
  echo "AVERTISSEMENT : PDF absent, le mail partira sans pièce jointe."
fi

# --- 4. Archive poussée dans le dépôt --------------------------------------
if [ -n "$(git status --porcelain archive/)" ]; then
  echo "Archivage de l'édition."
  git config user.name "veille-routine"
  git config user.email "veille-routine@users.noreply.github.com"
  git add archive/
  git commit --quiet -m "Édition du ${JOUR}"
  git push --quiet \
    "https://x-access-token:${GH_TOKEN}@github.com/${GH_DEPOT}.git" HEAD:main \
    && echo "Archive poussée." \
    || echo "AVERTISSEMENT : push refusé — vérifier que le jeton a la permission
    Contents en écriture. L'édition est produite malgré tout."
else
  echo "Rien à archiver."
fi

echo
echo "=== Prêt pour l'envoi ==="
echo "Objet    : $(cat travail/sujet.txt)"
echo "Corps    : ${RACINE}/travail/apercu.html"
echo "Jointe   : ${RACINE}/travail/piece_jointe.b64"
