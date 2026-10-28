#!/usr/bin/env bash
# installer.sh — Projet ParaLog (CESI, S3) — Script d'installation (A2) et droits (A3)
#
# En une seule commande :
#   1. vérifie les prérequis (Python 3.8+, multiprocessing, commandes du cours)
#   2. crée l'arborescence (data, src, scripts, resultats, archives, docs)
#   3. donne le projet au groupe de l'équipe (s'il existe et qu'on en fait partie)
#   4. pose les droits du tableau A3 (aucun 777)
# Le relancer ne casse rien : mkdir -p ne recrée pas un dossier existant,
# et les droits sont posés en valeur absolue (chmod 750, pas chmod +x).
#
# Utilisation (depuis n'importe où) :
#   bash scripts/installer.sh            -> groupe « paralog »
#   bash scripts/installer.sh GROUPE     -> autre nom de groupe
# Le groupe se crée une seule fois par un administrateur (le script n'appelle pas sudo) :
#   sudo groupadd paralog && sudo usermod -aG paralog UTILISATEUR
# Codes de retour : 0 = OK, 1 = prérequis manquant ou droits impossibles à poser,
#                   2 = mauvaise utilisation.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

if [ "$#" -gt 1 ]; then
    echo "Erreur : trop d'arguments." >&2
    echo "Utilisation : bash scripts/installer.sh [GROUPE]" >&2
    exit 2
fi
GROUPE="${1:-paralog}"

echo "Installation de ParaLog dans $RACINE"

# --- 1. Prérequis ----------------------------------------------------------
echo "1. Prérequis"
MANQUANTS=0
verifier() {  # $1 = libellé, $2 = commande de test
    if eval "$2" > /dev/null 2>&1; then
        echo "   [OK] $1"
    else
        echo "   [KO] $1" >&2
        MANQUANTS=$((MANQUANTS + 1))
    fi
}
verifier "Python 3.8 ou plus" "python3 -c 'import sys; assert sys.version_info >= (3, 8)'"
verifier "Module multiprocessing" "python3 -c 'import multiprocessing'"
for COMMANDE in grep cut sort uniq wc head tail find chmod chgrp tar gzip date; do
    verifier "Commande $COMMANDE" "command -v $COMMANDE"
done
if [ "$MANQUANTS" -gt 0 ]; then
    echo "Erreur : $MANQUANTS prérequis manquant(s). Sous Ubuntu / WSL : sudo apt install python3 coreutils tar gzip" >&2
    exit 1
fi

# --- 2. Arborescence -------------------------------------------------------
echo "2. Arborescence"
for DOSSIER in data src scripts resultats archives docs; do
    mkdir -p "$DOSSIER" || exit 1
    echo "   $DOSSIER/"
done

# --- 3. Groupe de l'équipe -------------------------------------------------
echo "3. Groupe « $GROUPE »"
# id -Gn : groupes du processus en cours (après usermod, il faut se reconnecter)
if id -Gn | tr ' ' '\n' | grep -qx "$GROUPE"; then
    # .git n'est pas concerné : on ne change que le contenu du projet
    if chgrp "$GROUPE" . && find . -maxdepth 1 -type f -exec chgrp "$GROUPE" {} + && \
       chgrp -R "$GROUPE" data src scripts resultats archives docs; then
        echo "   Projet attribué au groupe $GROUPE"
    else
        echo "Erreur : impossible d'attribuer le projet au groupe $GROUPE." >&2
        exit 1
    fi
else
    echo "   ATTENTION : vous n'êtes pas membre du groupe « $GROUPE » (ou il n'existe pas)." >&2
    echo "   Un administrateur doit lancer une fois :" >&2
    echo "     sudo groupadd $GROUPE && sudo usermod -aG $GROUPE $(id -un)" >&2
    echo "   puis se reconnecter et relancer : bash scripts/installer.sh" >&2
    echo "   Les droits sont posés quand même (le groupe reste votre groupe actuel)." >&2
fi

# --- 4. Droits (tableau A3) ------------------------------------------------
echo "4. Droits"
# Dossiers : propriétaire tout, groupe lecture + traversée, autres rien
chmod 750 . data src scripts docs || exit 1
# resultats : le groupe y écrit (lancer.sh) ; setgid (2) = les nouveaux fichiers gardent le groupe
chmod 2770 resultats || exit 1
# archives : propriétaire seul
chmod 700 archives || exit 1
# Sous-dossiers éventuels (__pycache__...) comme leur parent
find data src docs scripts -mindepth 1 -type d -exec chmod 750 {} + || exit 1
# Fichiers de données, code Python, docs, résultats : lus, jamais exécutés directement
find . -maxdepth 1 -type f -exec chmod 640 {} + || exit 1
find data src docs resultats -type f -exec chmod 640 {} + || exit 1
find scripts -type f ! -name '*.sh' -exec chmod 640 {} + || exit 1
# Scripts Bash : le groupe peut les lancer, les autres ni les lire ni les lancer
find scripts -type f -name '*.sh' -exec chmod 750 {} + || exit 1
# Archives : lisibles du seul propriétaire
find archives -type f -exec chmod 600 {} + || exit 1

ls -ld . data src scripts resultats archives docs | sed 's/^/   /'
echo "Installation terminée."
exit 0
