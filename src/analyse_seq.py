#!/usr/bin/env python3
"""
analyse_seq.py — Projet ParaLog (CESI, S3) — Version séquentielle (P1)

Analyse un journal d'accès Apache (format combined) et écrit le rapport
sur la sortie standard.

Utilisation (depuis la racine du dépôt) :
    python3 src/analyse_seq.py data/echantillon_access.log
"""
import sys
import time

from analyse_commun import analyser_lignes
from rapport import formater_rapport


def main():
    # Vérification de l'argument : exactement un chemin de journal
    if len(sys.argv) != 2:
        print("Erreur : il faut indiquer le journal à analyser.", file=sys.stderr)
        print("Utilisation : python3 src/analyse_seq.py JOURNAL", file=sys.stderr)
        return 2

    chemin = sys.argv[1]
    debut = time.perf_counter()
    try:
        # Lecture ligne par ligne (le fichier complet fait ~2 Go, on ne le charge jamais en entier).
        # errors="replace" : un octet invalide ne fait pas planter la lecture.
        with open(chemin, encoding="utf-8", errors="replace") as fichier:
            resultats = analyser_lignes(fichier)
    except FileNotFoundError:
        print(f"Erreur : fichier introuvable : {chemin}", file=sys.stderr)
        return 1
    except OSError as erreur:
        # Autres problèmes d'accès : dossier au lieu d'un fichier, droits insuffisants...
        print(f"Erreur : impossible de lire {chemin} : {erreur.strerror}", file=sys.stderr)
        return 1
    duree = time.perf_counter() - debut

    sys.stdout.write(formater_rapport(resultats, chemin, duree))
    return 0


if __name__ == "__main__":
    sys.exit(main())
