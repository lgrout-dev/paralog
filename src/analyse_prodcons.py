#!/usr/bin/env python3
"""
analyse_prodcons.py — Projet ParaLog (CESI, S3) — Variante producteur / consommateur (P10)

Un seul PRODUCTEUR (le processus principal) lit le journal par lots d'environ 1 Mo
et les dépose dans une FILE BORNÉE (au plus 2 × N lots en attente). N processus
CONSOMMATEURS retirent les lots de la file, les analysent avec la même fonction
qu'en P1 / P2 (analyser_lignes) et renvoient leurs résultats, que le principal fusionne.
Différence avec P2 : en P2, chaque worker lit lui-même son bloc du fichier ;
ici, toutes les données passent par le producteur puis par la file.
Le rapport est identique à celui de la version séquentielle (hors ligne du temps).

Utilisation (depuis la racine du dépôt) :
    python3 src/analyse_prodcons.py JOURNAL [N]
    python3 src/analyse_prodcons.py data/echantillon_access.log 4
N (nombre de consommateurs) est optionnel : par défaut, le nombre de cœurs de la machine.
"""
import os
import sys
import time
from multiprocessing import Process, Queue

from analyse_commun import analyser_lignes, fusionner
from analyse_par import lire_nombre_workers
from rapport import formater_rapport

# Taille d'un lot lu par le producteur. Un lot est envoyé tel quel (bytes) :
# c'est le consommateur qui le décode et le découpe en lignes.
TAILLE_LOT = 1024 * 1024


def lignes_des_lots(file_lots):
    """Générateur : renvoie une à une les lignes (str) des lots retirés de la file.

    S'arrête au marqueur de fin (None) envoyé par le producteur.
    Décodage et découpage identiques à P2 (errors="replace", split("\\n")).
    """
    while True:
        lot = file_lots.get()              # attend si la file est vide
        if lot is None:                    # marqueur de fin : plus rien à lire
            return
        lignes = lot.decode("utf-8", errors="replace").split("\n")
        if lignes[-1] == "":               # le lot finit par "\n" : dernier élément vide
            lignes.pop()
        yield from lignes


def consommer(file_lots, file_resultats):
    """Travail d'un consommateur : analyse tous les lots qu'il retire, puis envoie son résultat.

    Comme en P2, chaque consommateur a ses propres Counter : la seule donnée
    partagée est la file elle-même, protégée par les verrous internes de Queue.
    """
    file_resultats.put(analyser_lignes(lignes_des_lots(file_lots)))


def produire(fichier, file_lots):
    """Travail du producteur : lit le fichier par lots recalés sur les "\\n" et les met dans la file.

    put() attend tant que la file est pleine : le producteur ne peut jamais avoir
    plus de 2 × N lots d'avance, la mémoire reste bornée quelle que soit la taille du journal.
    """
    while True:
        lot = fichier.read(TAILLE_LOT)
        if not lot:                        # fin du fichier
            return
        if not lot.endswith(b"\n"):
            lot += fichier.readline()      # finit la ligne coupée : jamais de ligne sur deux lots
        file_lots.put(lot)


def main():
    # Vérification des arguments : JOURNAL obligatoire, N optionnel (comme P2)
    if len(sys.argv) not in (2, 3):
        print("Erreur : il faut indiquer le journal à analyser.", file=sys.stderr)
        print("Utilisation : python3 src/analyse_prodcons.py JOURNAL [N]", file=sys.stderr)
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

    # Même chronomètre que P2 : création des consommateurs, lecture, analyse et fusion
    debut = time.perf_counter()
    try:
        # Le fichier est ouvert AVANT de créer les consommateurs : s'il est absent,
        # on s'arrête tout de suite, sans laisser de consommateur attendre un lot.
        with open(chemin, "rb") as fichier:
            file_lots = Queue(maxsize=2 * n)       # la file bornée
            file_resultats = Queue()               # un résultat par consommateur
            consommateurs = [Process(target=consommer, args=(file_lots, file_resultats))
                             for _ in range(n)]
            for consommateur in consommateurs:
                consommateur.start()
            produire(fichier, file_lots)
            for _ in consommateurs:                 # un marqueur de fin par consommateur
                file_lots.put(None)
            # Les résultats sont lus AVANT join() : un processus qui a mis des données dans
            # une Queue ne se termine qu'une fois qu'elles ont été lues ; join() d'abord
            # pourrait attendre sans fin (consommateur bloqué sur un tube plein).
            resultats = fusionner([file_resultats.get() for _ in consommateurs])
            for consommateur in consommateurs:
                consommateur.join()
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


# Obligatoire avec multiprocessing (comme P2) : en mode « spawn » / « forkserver »,
# chaque consommateur réimporte ce fichier.
if __name__ == "__main__":
    sys.exit(main())
