#!/usr/bin/env bash
# mesurer_p8.sh — Projet ParaLog (CESI, S3) — Processus ou threads ? (P8)
#
# Mesure la même analyse avec des THREADS (src/analyse_threads.py) puis avec des
# PROCESSUS (src/analyse_par.py), pour 1, 2, 4 et 8 workers, ESSAIS fois chacune
# (3 par défaut), avec la version séquentielle comme référence.
# Pour chaque lancement, on relève :
#   - le « Temps d'analyse » affiché par le programme (même mesure qu'en P6) ;
#   - le temps CPU (user + sys) donné par la commande time de bash ;
#   - le temps réel de la commande, lu sur une horloge MONOTONE (voir horloge() plus bas).
# Cœurs occupés = CPU ÷ temps réel : nombre moyen de cœurs qui ont vraiment calculé.
# Chaque rapport est comparé à celui du séquentiel (hors temps) : si un seul diffère, on s'arrête.
#
# Utilisation (depuis n'importe où) :
#   bash scripts/mesurer_p8.sh data/access.log                -> mesures officielles
#   bash scripts/mesurer_p8.sh data/echantillon_access.log 1  -> essai rapide du script
#
# Fichiers écrits dans resultats/ (NOM = nom du journal sans .log, SYS = linux ou macos) :
#   mesures_p8_NOM_SYS.txt   tableau lisible (machine, temps, médianes, accélération, cœurs occupés)
#   mesures_p8_NOM_SYS.csv   données brutes de chaque essai
# SYS dans le nom : les mesures de deux machines ne s'écrasent pas.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

JOURNAL="${1:-}"
ESSAIS="${2:-3}"
if [ -z "$JOURNAL" ] || [ $# -gt 2 ]; then
    echo "Erreur : il faut indiquer le journal à mesurer." >&2
    echo "Utilisation : bash scripts/mesurer_p8.sh JOURNAL [ESSAIS]" >&2
    exit 2
fi
if [ ! -f "$JOURNAL" ]; then
    echo "Erreur : fichier introuvable : $JOURNAL" >&2
    exit 1
fi
if [ ! -r "$JOURNAL" ]; then
    echo "Erreur : impossible de lire $JOURNAL" >&2
    exit 1
fi
case "$ESSAIS" in
    ''|*[!0-9]*|0) echo "Erreur : ESSAIS doit être un entier supérieur ou égal à 1." >&2; exit 2 ;;
esac

case "$(uname -s)" in
    Darwin) SYS=macos ;;
    *)      SYS=linux ;;
esac
NOM="$(basename "$JOURNAL" .log)"
SORTIE_TXT="resultats/mesures_p8_${NOM}_$SYS.txt"
SORTIE_CSV="resultats/mesures_p8_${NOM}_$SYS.csv"
# "seq" = analyse_seq.py ; "tN" = analyse_threads.py avec N threads ; "pN" = analyse_par.py avec N processus
VERSIONS="seq t1 t2 t4 t8 p1 p2 p4 p8"
export LC_NUMERIC=C          # point décimal pour awk, sort et time
TIMEFORMAT="%U %S"           # time affiche : user sys (temps CPU, en secondes)

# Description de la machine (même méthode que mesurer.sh)
if command -v lscpu > /dev/null; then
    PROCESSEUR="$(lscpu | sed -n 's/^Model name:[[:space:]]*//p' | head -n 1)"
    PHYSIQUES="$(lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l | tr -d ' ')"
    LOGIQUES="$(nproc)"
else
    PROCESSEUR="$(sysctl -n machdep.cpu.brand_string 2> /dev/null)"
    PHYSIQUES="$(sysctl -n hw.physicalcpu 2> /dev/null)"
    LOGIQUES="$(sysctl -n hw.logicalcpu 2> /dev/null)"
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Heure lue sur l'horloge monotone (en secondes). On n'utilise pas le temps réel de time :
# il vient de l'horloge murale, que WSL recale régulièrement sur Windows (saut de -2,4 s
# observé le 28/10), ce qui donnait un temps réel plus court que le temps d'analyse.
# L'horloge monotone ne recule jamais : c'est aussi celle de time.perf_counter() dans nos programmes.
horloge() {
    python3 -c 'import time; print(time.monotonic())'
}

# Lance une version ; écrit son rapport dans $TMP/rapport.txt et
# affiche « temps_analyse réel user sys », ou rien en cas d'échec.
mesurer_une_fois() {
    case "$1" in
        seq) set -- src/analyse_seq.py "$JOURNAL" ;;
        t*)  set -- src/analyse_threads.py "$JOURNAL" "${1#t}" ;;
        p*)  set -- src/analyse_par.py "$JOURNAL" "${1#p}" ;;
    esac
    DEBUT="$(horloge)"
    # Les accolades permettent de rediriger la sortie de time (écrite sur stderr) vers un fichier
    { time python3 "$@" > "$TMP/rapport.txt" 2> "$TMP/erreurs.txt" ; } 2> "$TMP/time.txt" || return
    FIN="$(horloge)"
    REEL="$(awk -v d="$DEBUT" -v f="$FIN" 'BEGIN {printf "%.3f", f - d}')"
    TEMPS="$(tail -n 1 "$TMP/rapport.txt" | awk '{print $(NF-1)}')"
    [ -n "$TEMPS" ] && echo "$TEMPS $REEL $(tail -n 1 "$TMP/time.txt")"
}

# Les essais sont entrelacés (essai 1 de chaque version, puis essai 2...) :
# une perturbation passagère de la machine ne pénalise pas une seule version.
for ESSAI in $(seq 1 "$ESSAIS"); do
    for V in $VERSIONS; do
        MESURE="$(mesurer_une_fois "$V")"
        if [ -z "$MESURE" ]; then
            echo "Erreur : la version $V n'a pas donné de temps." >&2
            cat "$TMP/erreurs.txt" >&2
            exit 1
        fi
        # Même analyse : le rapport doit être celui du séquentiel, hors dernière ligne (le temps)
        sed '$d' "$TMP/rapport.txt" > "$TMP/rapport_sans_temps.txt"
        if [ ! -f "$TMP/reference.txt" ]; then
            mv "$TMP/rapport_sans_temps.txt" "$TMP/reference.txt"
        elif ! diff -q "$TMP/reference.txt" "$TMP/rapport_sans_temps.txt" > /dev/null; then
            echo "Erreur : le rapport de la version $V diffère de celui du séquentiel." >&2
            exit 1
        fi
        echo "$ESSAI $MESURE" >> "$TMP/$V"     # essai temps_analyse réel user sys
        echo "Essai $ESSAI/$ESSAIS, version $V : $(echo "$MESURE" | awk '{print $1}') s"
    done
done

# Médiane de la colonne COL d'un fichier de mesures
mediane() {
    awk -v c="$2" '{print $c}' "$1" | sort -n |
        awk '{t[NR] = $1} END {if (NR % 2) print t[(NR + 1) / 2]; else printf "%.3f\n", (t[NR / 2] + t[NR / 2 + 1]) / 2}'
}

MED_SEQ="$(mediane "$TMP/seq" 2)"
{
    echo "=== Mesures de performance ParaLog — P8 (processus ou threads ?) ==="
    echo
    echo "Journal    : $JOURNAL ($(wc -l < "$JOURNAL" | tr -d ' ') lignes)"
    echo "Machine    : $PROCESSEUR, $PHYSIQUES cœurs physiques, $LOGIQUES cœurs logiques"
    echo "Système    : $(uname -sr)"
    echo "Python     : $(python3 --version 2>&1)"
    echo "Date       : $(date '+%d/%m/%Y %H:%M')"
    echo "Essais     : $ESSAIS par version, entrelacés ; rapports tous identiques au séquentiel (hors temps)"
    echo
    printf "%-14s %-26s %9s %13s %16s\n" "Version" "Temps des essais (s)" "Médiane" "Accélération" "Cœurs occupés"
    for V in $VERSIONS; do
        case "$V" in
            seq) LIBELLE="séquentiel" ;;
            t*)  LIBELLE="${V#t} thread(s)" ;;
            p*)  LIBELLE="${V#p} processus" ;;
        esac
        MED="$(mediane "$TMP/$V" 2)"
        ACC="$(awk -v s="$MED_SEQ" -v p="$MED" 'BEGIN {printf "%.2f", s / p}')"
        # Cœurs occupés de chaque essai = (user + sys) ÷ réel, puis médiane
        awk '{printf "%.2f\n", ($4 + $5) / $3}' "$TMP/$V" > "$TMP/coeurs_$V"
        COEURS="$(mediane "$TMP/coeurs_$V" 1)"
        # printf compte en octets : "é" en prend 2, d'où une colonne plus large pour "séquentiel"
        if [ "$V" = "seq" ]; then LARGEUR=15; else LARGEUR=14; fi
        printf "%-${LARGEUR}s %-26s %9s %13s %16s\n" "$LIBELLE" "$(awk '{print $2}' "$TMP/$V" | paste -sd ' ' -)" \
            "$MED" "x$ACC" "$COEURS"
    done
    echo
    echo "Accélération  = médiane séquentielle ÷ médiane de la version."
    echo "Cœurs occupés = temps CPU (user + sys) ÷ temps réel de la commande (médiane des essais) :"
    echo "                1 = un seul cœur calcule à la fois ; N = N cœurs calculent en même temps."
} > "$SORTIE_TXT"

{
    echo "version,essai,temps_s,reel_s,user_s,sys_s"
    for V in $VERSIONS; do
        awk -v v="$V" '{print v "," $1 "," $2 "," $3 "," $4 "," $5}' "$TMP/$V"
    done
} > "$SORTIE_CSV"

echo
cat "$SORTIE_TXT"
echo "Écrit : $SORTIE_TXT et $SORTIE_CSV"
