#!/usr/bin/env bash
# lancer.sh — Projet ParaLog (CESI, S3) — Script de lancement (A4)
#
# Lance l'analyse parallèle (src/analyse_par.py) avec N workers et écrit
# le rapport dans un fichier horodaté de resultats/.
#
# Utilisation (depuis n'importe où) :
#   bash scripts/lancer.sh data/echantillon_access.log 4
#   bash scripts/lancer.sh data/access.log            -> N = nombre de cœurs
# Rapport écrit : resultats/rapport_AAAAMMJJ_HHMMSS_NOM_NN.txt (NOM = journal sans .log)
# Codes de retour : 0 = OK, 1 = fichier absent ou illisible, 2 = mauvaise utilisation.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "Erreur : il faut indiquer le journal à analyser." >&2
    echo "Utilisation : bash scripts/lancer.sh JOURNAL [N]" >&2
    exit 2
fi

JOURNAL="$1"
# N par défaut : nombre de cœurs disponibles (getconf marche sous Linux et macOS)
N="${2:-$(getconf _NPROCESSORS_ONLN)}"

# N doit être un entier >= 1 (pas vide, uniquement des chiffres, pas 0)
case "$N" in
    ''|*[!0-9]*|0*) echo "Erreur : N doit être un entier supérieur ou égal à 1 (reçu : $N)." >&2; exit 2 ;;
esac

if [ ! -e "$JOURNAL" ]; then
    echo "Erreur : fichier introuvable : $JOURNAL" >&2
    exit 1
fi
if [ ! -f "$JOURNAL" ] || [ ! -r "$JOURNAL" ]; then
    echo "Erreur : impossible de lire $JOURNAL (pas un fichier, ou droits insuffisants)." >&2
    exit 1
fi

HORODATAGE="$(date +%Y%m%d_%H%M%S)"
NOM="$(basename "$JOURNAL" .log)"
RAPPORT="resultats/rapport_${HORODATAGE}_${NOM}_N${N}.txt"

# umask 027 : le rapport est créé en 640 (tableau des droits A3), lisible par le groupe seulement
umask 027
echo "Analyse de $JOURNAL avec $N worker(s)..."
if ! python3 src/analyse_par.py "$JOURNAL" "$N" > "$RAPPORT"; then
    # On ne laisse pas un rapport vide ou incomplet dans resultats/
    rm -f "$RAPPORT"
    echo "Erreur : l'analyse a échoué, aucun rapport écrit." >&2
    exit 1
fi

echo "Rapport écrit : $RAPPORT"
tail -n 1 "$RAPPORT"
exit 0
