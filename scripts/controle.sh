#!/usr/bin/env bash
# controle.sh — Projet ParaLog (CESI, S3) — Chaîne de contrôle en ligne de commande (A5)
#
# Recalcule, sans Python, avec des commandes du cours reliées par des tubes
# (cut, sort, uniq -c, head, wc) :
#   1. le nombre de requêtes par code HTTP (9e champ)
#   2. les 10 adresses IP les plus actives (1er champ)
# et les enregistre par redirection dans resultats/controle_NOM.txt (NOM = journal sans .log).
# Ces nombres doivent être ceux du rapport Python (analyse_seq.py / analyse_par.py).
#
# Utilisation (depuis n'importe où) :
#   bash scripts/controle.sh data/echantillon_access.log
# Codes de retour : 0 = OK, 1 = fichier absent ou illisible, 2 = mauvaise utilisation.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

if [ "$#" -ne 1 ]; then
    echo "Erreur : il faut indiquer le journal à contrôler." >&2
    echo "Utilisation : bash scripts/controle.sh JOURNAL" >&2
    exit 2
fi

JOURNAL="$1"
if [ ! -e "$JOURNAL" ]; then
    echo "Erreur : fichier introuvable : $JOURNAL" >&2
    exit 1
fi
if [ ! -f "$JOURNAL" ] || [ ! -r "$JOURNAL" ]; then
    echo "Erreur : impossible de lire $JOURNAL (pas un fichier, ou droits insuffisants)." >&2
    exit 1
fi

# Tri octet par octet, comme Python : même ordre pour les ex aequo, et tri plus rapide
export LC_ALL=C

SORTIE="resultats/controle_$(basename "$JOURNAL" .log).txt"

# Les accolades regroupent toutes les sorties : une seule redirection vers le fichier
{
    echo "=== Contrôle ParaLog (cut | sort | uniq -c) ==="
    echo "Journal contrôlé : $JOURNAL"
    echo "Lignes du fichier : $(wc -l < "$JOURNAL")"
    echo
    echo "--- 1. Requêtes par code HTTP (nombre, code) ---"
    # sort -n : codes triés numériquement, puis uniq -c compte chaque code
    cut -d' ' -f9 "$JOURNAL" | sort -n | uniq -c
    echo
    echo "--- 2. Top 10 des adresses IP (nombre, IP) ---"
    # sort -k1,1nr -k2,2 : nombre décroissant, puis IP croissante (même règle que rapport.py)
    cut -d' ' -f1 "$JOURNAL" | sort | uniq -c | sort -k1,1nr -k2,2 | head -n 10
} > "$SORTIE"

echo "Contrôle écrit : $SORTIE"
exit 0
