#!/usr/bin/env bash
# archiver.sh — Projet ParaLog (CESI, S3) — Script d'archivage (A8)
#
# Crée dans archives/ une archive .tar.gz horodatée du dossier resultats/,
# lisible du seul propriétaire (droits 600, dossier archives/ en 700).
#
# Utilisation (depuis n'importe où) :
#   bash scripts/archiver.sh
# Archive créée : archives/resultats_AAAAMMJJ_HHMMSS.tar.gz
# Codes de retour : 0 = OK, 1 = resultats/ absent ou archivage impossible, 2 = mauvaise utilisation.

RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1

if [ "$#" -ne 0 ]; then
    echo "Erreur : ce script ne prend aucun argument." >&2
    echo "Utilisation : bash scripts/archiver.sh" >&2
    exit 2
fi

if [ ! -d resultats ] || [ ! -r resultats ]; then
    echo "Erreur : dossier resultats/ introuvable ou illisible." >&2
    exit 1
fi

# umask 077 : tout ce que le script crée est réservé au propriétaire dès sa création
# (sinon l'archive serait lisible par les autres entre sa création et le chmod)
umask 077
mkdir -p archives
chmod 700 archives

ARCHIVE="archives/resultats_$(date +%Y%m%d_%H%M%S).tar.gz"
if [ -e "$ARCHIVE" ]; then
    echo "Erreur : $ARCHIVE existe déjà (relancer dans une seconde)." >&2
    exit 1
fi

# -c créer, -z compresser (gzip), -f nom de l'archive
# Chemin relatif : l'archive contient « resultats/... », pas le chemin de la machine
if ! tar -czf "$ARCHIVE" resultats; then
    rm -f "$ARCHIVE"
    echo "Erreur : l'archivage a échoué." >&2
    exit 1
fi
chmod 600 "$ARCHIVE"

echo "Archive créée : $ARCHIVE ($(tar -tzf "$ARCHIVE" | wc -l | tr -d ' ') éléments)"
ls -l "$ARCHIVE"
exit 0
