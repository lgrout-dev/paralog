#!/usr/bin/env bash
# observer.sh — Projet ParaLog (CESI, S3) — Observation du système (A9)
#
# Lance l'analyse parallèle (src/analyse_par.py) en arrière-plan et, pendant qu'elle
# tourne, prend une « photo » avec ps toutes les INTERVALLE secondes : le processus
# principal et tous ses descendants (forkserver, resource_tracker, workers), avec
#   PID, PPID (le parent), STAT (l'état), PSR (le cœur utilisé), %CPU, NLWP (nombre de threads).
# À la fin, un résumé donne, pour chaque processus, les états et les cœurs vus.
#
# Utilisation (depuis n'importe où, sous Linux) :
#   bash scripts/observer.sh data/access.log 4            -> relevé officiel (photo toutes les 0,2 s)
#   bash scripts/observer.sh data/echantillon_access.log 4 0.01
#        -> essai sur l'échantillon : l'analyse dure moins de 0,1 s, il faut des photos rapprochées
# Relevé écrit : resultats/observation_NOM_NN.txt (NOM = journal sans .log)
# Codes de retour : 0 = OK, 1 = fichier absent ou illisible, ps incompatible ou analyse
# en échec, 2 = mauvaise utilisation.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

if [ "$#" -gt 3 ]; then
    echo "Erreur : trop d'arguments." >&2
    echo "Utilisation : bash scripts/observer.sh [JOURNAL] [N] [INTERVALLE]" >&2
    exit 2
fi

JOURNAL="${1:-data/echantillon_access.log}"
N="${2:-4}"
INTERVALLE="${3:-0.2}"        # secondes entre deux photos

# Mêmes contrôles que lancer.sh
case "$N" in
    ''|*[!0-9]*|0*) echo "Erreur : N doit être un entier supérieur ou égal à 1 (reçu : $N)." >&2; exit 2 ;;
esac
# INTERVALLE : chiffres avec au plus un point (0.2, 1, 0.01), et strictement positif
case "$INTERVALLE" in
    ''|.|*[!0-9.]*|*.*.*) INTERVALLE_OK=non ;;
    *) INTERVALLE_OK="$(awk -v i="$INTERVALLE" 'BEGIN {print (i > 0) ? "oui" : "non"}')" ;;
esac
if [ "$INTERVALLE_OK" != oui ]; then
    echo "Erreur : INTERVALLE doit être un nombre de secondes supérieur à 0, avec un point (reçu : $INTERVALLE)." >&2
    exit 2
fi
if [ ! -e "$JOURNAL" ]; then
    echo "Erreur : fichier introuvable : $JOURNAL" >&2
    exit 1
fi
if [ ! -f "$JOURNAL" ] || [ ! -r "$JOURNAL" ]; then
    echo "Erreur : impossible de lire $JOURNAL (pas un fichier, ou droits insuffisants)." >&2
    exit 1
fi

# La colonne psr (cœur utilisé) n'existe que dans le ps de Linux (procps), pas sous macOS
if ! ps -o psr= -p $$ > /dev/null 2>&1; then
    echo "Erreur : ce ps ne sait pas afficher le cœur utilisé (psr) : Linux uniquement." >&2
    exit 1
fi

NOM="$(basename "$JOURNAL" .log)"
SORTIE="resultats/observation_${NOM}_N${N}.txt"
COLONNES="pid=,ppid=,stat=,psr=,pcpu=,nlwp=,args="

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Temps écoulé depuis le démarrage de Linux, lu dans /proc/uptime (horloge monotone :
# elle ne saute pas quand WSL recale l'heure sur Windows, voir mesurer_p8.sh).
uptime_s() {
    read -r UP _ < /proc/uptime
    echo "$UP"
}

# Photo : garde le processus principal et ses descendants, et leur donne un rôle.
# ps liste tous les processus ; awk part du principal et ajoute les enfants de
# processus déjà gardés, jusqu'à ce qu'il n'y en ait plus de nouveaux.
photo() {
    ps -e -o "$COLONNES" | awk -v racine="$PID" '
        { pid[NR] = $1; ppid[NR] = $2; ligne[NR] = $0 }
        END {
            garde[racine] = 1
            do {
                ajout = 0
                for (i = 1; i <= NR; i++)
                    if (!(pid[i] in garde) && (ppid[i] in garde)) { garde[pid[i]] = 1; ajout = 1 }
            } while (ajout)
            for (i = 1; i <= NR; i++) {
                if (!(pid[i] in garde)) continue
                if (pid[i] == racine)                    role = "principal"
                else if (ligne[i] ~ /resource_tracker/)  role = "resource_tracker"
                else if (ligne[i] ~ /forkserver/ && ppid[i] == racine) role = "forkserver"
                else                                     role = "worker"
                split(ligne[i], c, " ")
                printf "  %-16s %7s %7s  %-5s %3s %5s %4s\n", role, c[1], c[2], c[3], c[4], c[5], c[6]
            }
        }'
}

umask 027
DEBUT="$(uptime_s)"
python3 src/analyse_par.py "$JOURNAL" "$N" > "$TMP/rapport.txt" 2> "$TMP/erreurs.txt" &
PID=$!

# Photos tant que le programme tourne (kill -0 teste seulement qu'il existe encore)
NB_PHOTOS=0
while kill -0 "$PID" 2> /dev/null; do
    T="$(awk -v d="$DEBUT" -v f="$(uptime_s)" 'BEGIN {printf "%.2f", f - d}')"
    PHOTO="$(photo)"
    # Le programme a pu se terminer entre kill -0 et ps : photo vide, on ne la garde pas
    if [ -n "$PHOTO" ]; then
        NB_PHOTOS=$((NB_PHOTOS + 1))
        { echo "--- photo $NB_PHOTOS, t = $T s"; echo "$PHOTO"; } >> "$TMP/photos.txt"
    fi
    sleep "$INTERVALLE"
done

wait "$PID"
CODE=$?
if [ "$CODE" -ne 0 ]; then
    echo "Erreur : l'analyse a échoué (code $CODE), pas de relevé." >&2
    cat "$TMP/erreurs.txt" >&2
    exit 1
fi
if [ "$NB_PHOTOS" -eq 0 ]; then
    echo "Erreur : l'analyse a fini avant la première photo, aucun relevé." >&2
    exit 1
fi

# Description de la machine (même méthode que mesurer.sh)
PROCESSEUR="$(lscpu | sed -n 's/^Model name:[[:space:]]*//p' | head -n 1)"
PHYSIQUES="$(lscpu -p=Core,Socket | grep -v '^#' | sort -u | wc -l | tr -d ' ')"
LOGIQUES="$(nproc)"

{
    echo "=== Observation du système pendant une exécution de P2 (A9) ==="
    echo "Commande   : python3 src/analyse_par.py $JOURNAL $N"
    echo "Date       : $(date '+%d/%m/%Y %H:%M:%S')"
    echo "Machine    : $PROCESSEUR, $PHYSIQUES cœurs physiques, $LOGIQUES cœurs logiques (numérotés 0 à $((LOGIQUES - 1)))"
    echo "Python     : $(python3 --version 2>&1)"
    echo "Photos     : $NB_PHOTOS, intervalle demandé $INTERVALLE s (ps lui-même prend un peu de temps) ; $(tail -n 1 "$TMP/rapport.txt")"
    echo
    echo "Colonnes : PPID = parent ; STAT = état (R en cours d'exécution, S endormi en attente,"
    echo "D attente disque, Z zombie, l = a plusieurs threads, s = chef de session, + = premier plan) ;"
    echo "PSR = cœur utilisé ; %CPU = temps CPU ÷ durée de vie (moyenne, pas instantané) ; NLWP = threads."
    echo
    printf "  %-16s %7s %7s  %-5s %3s %5s %4s\n" "RÔLE" "PID" "PPID" "STAT" "PSR" "%CPU" "NLWP"
    cat "$TMP/photos.txt"
    echo
    echo "=== Résumé par processus (états et cœurs vus sur l'ensemble des photos) ==="
    # Chaque ligne de photo : rôle pid ppid stat psr %cpu nlwp
    awk '
        /^  / {
            if (!($2 in role)) { ordre[++n] = $2; role[$2] = $1 }
            photos[$2]++
            etat = substr($4, 1, 1)
            if (index(" " etats[$2] " ", " " etat " ") == 0) etats[$2] = etats[$2] (etats[$2] ? " " : "") etat
            if (index(" " coeurs[$2] " ", " " $5 " ") == 0)  coeurs[$2] = coeurs[$2] (coeurs[$2] ? " " : "") $5
        }
        END {
            printf "  %-16s %7s %7s  %-8s %s\n", "RÔLE", "PID", "PHOTOS", "ÉTATS", "CŒURS"
            for (i = 1; i <= n; i++) {
                p = ordre[i]
                printf "  %-16s %7s %7s  %-8s %s\n", role[p], p, photos[p], etats[p], coeurs[p]
            }
        }' "$TMP/photos.txt"
} > "$SORTIE"

echo "Relevé écrit : $SORTIE ($NB_PHOTOS photos)"
exit 0
