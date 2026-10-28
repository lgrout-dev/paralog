#!/usr/bin/env bash
# nettoyer.sh — Projet ParaLog (CESI, S3) — Script de nettoyage (A7)
#
# Supprime, après confirmation (ou sans la demander avec l'option -o) :
#   - les fichiers temporaires : dossiers __pycache__, fichiers *.pyc, *.tmp, *~
#   - les rapports de lancer.sh (resultats/rapport_AAAAMMJJ_...txt) de plus de N jours
# Ne touche jamais à data/ ni à archives/ : la recherche ne parcourt que
# src/, scripts/, resultats/ et docs/. Les résultats officiels (rapport_seq.txt,
# mesures, graphique) ne sont pas concernés.
#
# Utilisation (depuis n'importe où) :
#   bash scripts/nettoyer.sh          -> rapports de plus de 7 jours, avec confirmation
#   bash scripts/nettoyer.sh 0        -> tous les rapports de lancer.sh
#   bash scripts/nettoyer.sh -o 30    -> plus de 30 jours, sans confirmation
# Codes de retour : 0 = OK (ou suppression refusée), 2 = mauvaise utilisation.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

utilisation() {
    echo "Utilisation : bash scripts/nettoyer.sh [-o] [N]   (N = âge en jours, 7 par défaut)" >&2
    exit 2
}

OUI=0
N=""
for ARG in "$@"; do
    case "$ARG" in
        -o) OUI=1 ;;
        ''|*[!0-9]*) echo "Erreur : argument inconnu : $ARG" >&2; utilisation ;;
        *)  if [ -n "$N" ]; then echo "Erreur : N est donné deux fois." >&2; utilisation; fi
            N="$ARG" ;;
    esac
done
N="${N:-7}"

# Dossiers parcourus : data/ et archives/ n'en font volontairement pas partie
DOSSIERS="src scripts resultats docs"

# Liste ce qu'il faut supprimer (un chemin par ligne)
# -mmin +X : modifié il y a plus de X minutes, soit N jours = N × 1440 minutes
lister() {
    find $DOSSIERS -type d -name __pycache__ -prune
    find $DOSSIERS -type f \( -name '*.pyc' -o -name '*.tmp' -o -name '*~' \) -not -path '*/__pycache__/*'
    if [ "$N" -eq 0 ]; then
        # N = 0 : tous les rapports (-mmin +0 oublierait ceux de moins d'une minute)
        find resultats -maxdepth 1 -type f -name 'rapport_[0-9]*.txt'
    else
        find resultats -maxdepth 1 -type f -name 'rapport_[0-9]*.txt' -mmin +$((N * 1440))
    fi
}

A_SUPPRIMER="$(lister 2> /dev/null)"
if [ -z "$A_SUPPRIMER" ]; then
    echo "Rien à supprimer (fichiers temporaires, rapports de plus de $N jour(s))."
    exit 0
fi

echo "Éléments à supprimer :"
echo "$A_SUPPRIMER" | sed 's/^/  /'
NOMBRE="$(echo "$A_SUPPRIMER" | wc -l | tr -d ' ')"

if [ "$OUI" -eq 0 ]; then
    read -r -p "Supprimer ces $NOMBRE élément(s) ? [o/N] " REPONSE
    case "$REPONSE" in
        o|O|oui|OUI) ;;
        *) echo "Rien n'a été supprimé."; exit 0 ;;
    esac
fi

# Un chemin par ligne : les noms du projet ne contiennent pas d'espace
echo "$A_SUPPRIMER" | while read -r CHEMIN; do
    rm -rf -- "$CHEMIN"
done
echo "$NOMBRE élément(s) supprimé(s)."
exit 0
