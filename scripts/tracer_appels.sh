#!/usr/bin/env bash
# tracer_appels.sh — Projet ParaLog (CESI, S3) — Appels système du schéma en couches (A6)
#
# Lance scripts/lancer.sh sous strace -f (qui suit aussi les processus fils), puis
# affiche, processus par processus, les appels système qui illustrent le schéma :
#   execve (lancer un programme), clone / vfork (créer un processus),
#   openat / lseek / read (lire le journal), dup2 / write (écrire le rapport).
# La trace complète est écrite dans un dossier temporaire, supprimé à la fin.
#
# Utilisation (depuis n'importe où, sous Linux) :
#   bash scripts/tracer_appels.sh                              -> échantillon, 2 workers
#   bash scripts/tracer_appels.sh data/echantillon_access.log 4
# Prérequis : strace (sudo apt install strace).
# Codes de retour : 0 = OK, 1 = strace absent ou lancement en échec, 2 = mauvaise utilisation.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

if [ "$#" -gt 2 ]; then
    echo "Erreur : trop d'arguments." >&2
    echo "Utilisation : bash scripts/tracer_appels.sh [JOURNAL] [N]" >&2
    exit 2
fi

JOURNAL="${1:-data/echantillon_access.log}"
N="${2:-2}"

if ! command -v strace > /dev/null 2>&1; then
    echo "Erreur : strace est introuvable (Linux uniquement). Installation : sudo apt install strace" >&2
    exit 1
fi

# Dossier temporaire supprimé automatiquement à la fin du script
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# -f  : suit les processus fils (python3, forkserver, workers)
# -ff : un fichier de trace par processus (trace.PID), donc des lignes jamais coupées
# -s  : tronque les chaînes affichées à 80 caractères
# lancer.sh vérifie lui-même le journal et N : en cas d'erreur, on renvoie son code.
strace -f -ff -s 80 -o "$TMP/trace" bash scripts/lancer.sh "$JOURNAL" "$N"
CODE=$?
if [ "$CODE" -ne 0 ]; then
    echo "Erreur : le lancement a échoué (code $CODE), pas de résumé." >&2
    exit "$CODE"
fi

echo
echo "Appels système relevés (un bloc par processus, dans l'ordre des PID) :"
echo

# Un fichier par processus ; tri numérique sur le PID (après le point)
for FICHIER in $(ls "$TMP"/trace.* | sort -t. -k2,2n); do
    awk -v pid="${FICHIER##*.}" -v journal="$JOURNAL" '
        # Garde une ligne ; si elle est trop longue, on coupe le milieu mais on garde le résultat (= ...)
        function garder(texte,    resultat) {
            if (length(texte) > 110) {
                resultat = texte
                sub(/.* = /, "= ", resultat)
                texte = substr(texte, 1, 90) " ... " resultat
            }
            lignes[++n] = "    " texte
        }

        # Résumé des lectures du journal (appelé à sa fermeture ou en fin de trace)
        function resumer_lectures() {
            if (lectures > 0) garder(sprintf("read(journal) x %d : %d octets lus au total", lectures, octets))
            lectures = 0; octets = 0
        }

        BEGIN { fd = -1; fd_rapport = -1 }

        # execve : le processus devient un autre programme ; le programme lancé donne son rôle
        /^execve\(/ && / = 0$/ {
            split($0, morceaux, "\"")          # morceaux[2] = chemin du programme
            if (morceaux[2] ~ /python3$/) {
                if ($0 ~ /forkserver/)            role = "forkserver de Python (crée les workers)"
                else if ($0 ~ /resource_tracker/) role = "resource_tracker de Python"
                else                              role = "python3 : programme principal"
            }
            else if (morceaux[2] ~ /bash$/) role = "bash : scripts/lancer.sh"
            else                            role = "commande " morceaux[2]
            garder($0); next
        }

        # Création de processus. Les threads (CLONE_THREAD) sont seulement comptés.
        /^(clone|clone3|fork|vfork)\(/ {
            if ($0 ~ /CLONE_THREAD/) { threads++; next }
            if (match($0, /flags=[^,]*/)) {
                garder("clone(" substr($0, RSTART, RLENGTH) ", ...) = " $NF)
            }
            else garder($0)
            next
        }

        # Ouverture du journal : on retient son descripteur (dernier champ, après "=")
        /^openat\(/ && index($0, "\"" journal "\"") {
            fd = $NF
            if (role == "") role = "worker (créé par clone, sans execve)"
            garder($0); next
        }

        # Redirection > de bash : création du rapport, puis dup2 vers la sortie standard (1)
        /^openat\(.*resultats\/rapport_.*O_CREAT/ { fd_rapport = $NF; garder($0); next }
        fd_rapport != -1 && $0 ~ "^dup2\\(" fd_rapport ", 1\\)" { garder($0); next }

        # Sur le journal : positionnement au début du bloc, lectures comptées, fermeture
        fd != -1 && $0 ~ "^lseek\\(" fd ", [0-9]+, SEEK_SET" { garder($0); next }
        fd != -1 && $0 ~ "^read\\(" fd ","                   { lectures++; octets += $NF; next }
        fd != -1 && $0 ~ "^close\\(" fd "\\)"                { resumer_lectures(); fd = -1; next }

        # Écriture du rapport sur la sortie standard
        /^write\(1, "=== Rapport/ { garder($0); next }

        END {
            resumer_lectures()
            if (threads > 0)  garder(sprintf("clone3(CLONE_VM|CLONE_THREAD...) x %d : threads, mémoire partagée", threads))
            if (n == 0) exit
            if (role == "") role = "sous-shell bash (clone sans execve)"
            printf "PID %s — %s\n", pid, role
            for (i = 1; i <= n; i++) print lignes[i]
        }
    ' "$FICHIER"
done
exit 0
