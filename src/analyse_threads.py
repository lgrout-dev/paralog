#!/usr/bin/env python3
"""
analyse_threads.py — Projet ParaLog (CESI, S3) — Variante avec des threads (P8)

Même analyse que la version parallèle (P2), mais les N workers sont des THREADS
d'un seul processus au lieu de N processus. Tout le reste est repris de P2 sans
modification (découpage en blocs, lecture d'un bloc, analyse, fusion) : la seule
différence entre les deux programmes est la ligne qui crée le pool.
Le rapport est identique à celui de la version séquentielle (hors ligne du temps).

Utilisation (depuis la racine du dépôt) :
    python3 src/analyse_threads.py JOURNAL [N]
    python3 src/analyse_threads.py data/echantillon_access.log 4
N (nombre de threads) est optionnel : par défaut, le nombre de cœurs de la machine.
"""
import os
import sys
import time
# ThreadPool a la même interface que multiprocessing.Pool (starmap...), mais ses
# workers sont des threads : même mémoire, même interpréteur, donc un seul GIL.
from multiprocessing.pool import ThreadPool

from analyse_commun import fusionner
from analyse_par import analyser_bloc, calculer_blocs, lire_nombre_workers
from rapport import formater_rapport


def main():
    # Vérification des arguments : JOURNAL obligatoire, N optionnel (comme P2)
    if len(sys.argv) not in (2, 3):
        print("Erreur : il faut indiquer le journal à analyser.", file=sys.stderr)
        print("Utilisation : python3 src/analyse_threads.py JOURNAL [N]", file=sys.stderr)
        return 2

    chemin = sys.argv[1]
    if len(sys.argv) == 3:
        n = lire_nombre_workers(sys.argv[2])
        if n is None:
            print(f"Erreur : N doit être un entier supérieur ou égal à 1 (reçu : {sys.argv[2]}).",
                  file=sys.stderr)
            return 2
    else:
        n = os.cpu_count() or 1

    # Même chronomètre que P2 : découpage, création des threads, analyse et fusion
    debut = time.perf_counter()
    try:
        blocs = calculer_blocs(chemin, n)
        # Chaque thread a ses propres Counter (créés dans analyser_bloc) et les renvoie :
        # comme en P2, aucune donnée n'est modifiée par deux threads, donc pas de verrou.
        with ThreadPool(processes=n) as pool:
            resultats_blocs = pool.starmap(analyser_bloc, [(chemin, d, f) for d, f in blocs])
        resultats = fusionner(resultats_blocs)
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
