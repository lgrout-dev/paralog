#!/usr/bin/env bash
# tester_p2.sh — Projet ParaLog (CESI, S3) — Test des résultats identiques (P3)
#
# Compare, avec diff, le rapport séquentiel (P1) et les rapports parallèles (P2)
# pour 1, 2, 4 et 8 workers. La dernière ligne (temps d'analyse) est exclue.
#
# Utilisation (depuis n'importe où) :
#   bash scripts/tester_p2.sh                    -> échantillon (data/echantillon_access.log)
#   bash scripts/tester_p2.sh data/access.log    -> fichier complet (plusieurs minutes)
# Code de retour : 0 si tous les rapports sont identiques, 1 sinon.

# Racine du dépôt, déduite de l'emplacement du script (aucun chemin absolu en dur)
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

JOURNAL="${1:-data/echantillon_access.log}"
if [ ! -f "$JOURNAL" ]; then
    echo "Erreur : fichier introuvable : $JOURNAL" >&2
    exit 1
fi

# Dossier temporaire supprimé automatiquement à la fin du script
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "Journal : $JOURNAL"
echo "Référence : version séquentielle..."
python3 src/analyse_seq.py "$JOURNAL" > "$TMP/seq.txt" || exit 1
tail -n 1 "$TMP/seq.txt"

ECHECS=0
for N in 1 2 4 8; do
    python3 src/analyse_par.py "$JOURNAL" "$N" > "$TMP/par_$N.txt" || exit 1
    # sed '$d' retire la dernière ligne (le temps), seule différence attendue
    if diff <(sed '$d' "$TMP/seq.txt") <(sed '$d' "$TMP/par_$N.txt") > "$TMP/diff_$N.txt"; then
        echo "N=$N : IDENTIQUE  ($(tail -n 1 "$TMP/par_$N.txt"))"
    else
        echo "N=$N : DIFFÉRENT"
        cat "$TMP/diff_$N.txt"
        ECHECS=$((ECHECS + 1))
    fi
done

if [ "$ECHECS" -eq 0 ]; then
    echo "Résultat : OK, les rapports séquentiel et parallèles sont identiques (hors temps)."
    exit 0
fi
echo "Résultat : ÉCHEC, $ECHECS rapport(s) différent(s)." >&2
exit 1
