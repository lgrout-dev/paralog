#!/usr/bin/env bash
# mesurer.sh — Projet ParaLog (CESI, S3) — Mesures de performance (P6)
#
# Mesure le temps de la version séquentielle puis de la version parallèle
# avec 1, 2, 4 et 8 workers, ESSAIS fois chacune (3 par défaut).
# Calcule la médiane de chaque version et l'accélération (médiane séq. ÷ médiane par.).
#
# Utilisation (depuis n'importe où) :
#   bash scripts/mesurer.sh data/access.log          -> mesures officielles (~15 min)
#   bash scripts/mesurer.sh data/echantillon_access.log 1   -> essai rapide du script
#
# Fichiers écrits dans resultats/ (NOM = nom du journal sans .log) :
#   mesures_p2_NOM.txt   tableau lisible (machine, temps, médianes, accélération)
#   mesures_p2_NOM.csv   mêmes données, pour tracer le graphique

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

JOURNAL="${1:-}"
ESSAIS="${2:-3}"
if [ -z "$JOURNAL" ]; then
    echo "Erreur : il faut indiquer le journal à mesurer." >&2
    echo "Utilisation : bash scripts/mesurer.sh JOURNAL [ESSAIS]" >&2
    exit 2
fi
if [ ! -f "$JOURNAL" ]; then
    echo "Erreur : fichier introuvable : $JOURNAL" >&2
    exit 1
fi
case "$ESSAIS" in
    ''|*[!0-9]*|0) echo "Erreur : ESSAIS doit être un entier supérieur ou égal à 1." >&2; exit 2 ;;
esac

NOM="$(basename "$JOURNAL" .log)"
SORTIE_TXT="resultats/mesures_p2_$NOM.txt"
SORTIE_CSV="resultats/mesures_p2_$NOM.csv"
VERSIONS="seq 1 2 4 8"      # "seq" = analyse_seq.py ; un nombre = analyse_par.py avec N workers
export LC_NUMERIC=C          # point décimal pour awk et sort

# Description de la machine (Linux : lscpu / nproc ; macOS : sysctl)
# On distingue les cœurs physiques des cœurs logiques (hyperthreading : 2 logiques par physique),
# car c'est le nombre de cœurs physiques qui limite l'accélération.
if command -v lscpu > /dev/null; then
    PROCESSEUR="$(lscpu | sed -n 's/^Model name:[[:space:]]*//p' | head -n 1)"
    # Une ligne par cœur logique "cœur,socket" : les couples différents = les cœurs physiques
    PHYSIQUES="$(lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l | tr -d ' ')"
    LOGIQUES="$(nproc)"
else
    PROCESSEUR="$(sysctl -n machdep.cpu.brand_string 2> /dev/null)"
    PHYSIQUES="$(sysctl -n hw.physicalcpu 2> /dev/null)"
    LOGIQUES="$(sysctl -n hw.logicalcpu 2> /dev/null)"
fi

# Lance une version et affiche son temps (nombre de la ligne « Temps d'analyse : X s »)
mesurer_une_fois() {
    if [ "$1" = "seq" ]; then
        python3 src/analyse_seq.py "$JOURNAL"
    else
        python3 src/analyse_par.py "$JOURNAL" "$1"
    fi | tail -n 1 | awk '{print $(NF-1)}'
}

# Les essais sont entrelacés (essai 1 de chaque version, puis essai 2...) :
# une perturbation passagère de la machine ne pénalise pas une seule version.
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
for ESSAI in $(seq 1 "$ESSAIS"); do
    for V in $VERSIONS; do
        T="$(mesurer_une_fois "$V")"
        if [ -z "$T" ]; then
            echo "Erreur : la version $V n'a pas donné de temps." >&2
            exit 1
        fi
        echo "$T" >> "$TMP/$V"
        echo "Essai $ESSAI/$ESSAIS, version $V : $T s"
    done
done

# Médiane d'une liste de temps (un par ligne)
mediane() {
    sort -n "$1" | awk '{t[NR] = $1} END {if (NR % 2) print t[(NR + 1) / 2]; else printf "%.3f\n", (t[NR / 2] + t[NR / 2 + 1]) / 2}'
}

MED_SEQ="$(mediane "$TMP/seq")"
{
    echo "=== Mesures de performance ParaLog — P2 (version parallèle) ==="
    echo
    echo "Journal    : $JOURNAL ($(wc -l < "$JOURNAL" | tr -d ' ') lignes)"
    echo "Machine    : $PROCESSEUR, $PHYSIQUES cœurs physiques, $LOGIQUES cœurs logiques"
    echo "Python     : $(python3 --version 2>&1)"
    echo "Date       : $(date '+%d/%m/%Y %H:%M')"
    echo "Essais     : $ESSAIS par version (temps = « Temps d'analyse » affiché par le programme)"
    echo
    printf "%-12s %-30s %10s %13s\n" "Version" "Temps des essais (s)" "Médiane" "Accélération"
    for V in $VERSIONS; do
        if [ "$V" = "seq" ]; then LIBELLE="séquentiel"; else LIBELLE="$V worker(s)"; fi
        MED="$(mediane "$TMP/$V")"
        ACC="$(awk -v s="$MED_SEQ" -v p="$MED" 'BEGIN {printf "%.2f", s / p}')"
        # printf compte en octets : "é" en prend 2, d'où une colonne plus large pour "séquentiel"
        if [ "$V" = "seq" ]; then LARGEUR=13; else LARGEUR=12; fi
        printf "%-${LARGEUR}s %-30s %10s %13s\n" "$LIBELLE" "$(paste -sd ' ' "$TMP/$V")" "$MED" "x$ACC"
    done
    echo
    echo "Accélération = médiane séquentielle ÷ médiane de la version."
} > "$SORTIE_TXT"

{
    echo "version,essai,temps_s"
    for V in $VERSIONS; do
        awk -v v="$V" '{print v "," NR "," $1}' "$TMP/$V"
    done
} > "$SORTIE_CSV"

echo
cat "$SORTIE_TXT"
echo "Écrit : $SORTIE_TXT et $SORTIE_CSV"
