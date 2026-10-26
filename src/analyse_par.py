#!/usr/bin/env python3
"""
analyse_par.py — Projet ParaLog (CESI, S3) — Version parallèle (P2)

Découpe le journal en N blocs d'octets, fait analyser chaque bloc par un
processus (worker), puis fusionne les résultats. Le rapport est identique
à celui de la version séquentielle (hors ligne du temps).

Utilisation (depuis la racine du dépôt) :
    python3 src/analyse_par.py JOURNAL [N]
    python3 src/analyse_par.py data/echantillon_access.log 4
N (nombre de workers) est optionnel : par défaut, le nombre de cœurs de la machine.
"""
import os
import sys
import time
from multiprocessing import Pool

from analyse_commun import analyser_lignes, fusionner
from rapport import formater_rapport

# Un worker lit son bloc par morceaux de 16 Mo : la mémoire reste bornée
# (un bloc peut faire ~1,9 Go avec 1 worker) et le décodage se fait en gros.
TAILLE_LECTURE = 16 * 1024 * 1024


def calculer_blocs(chemin, n):
    """Découpe le fichier en n blocs (debut, fin) d'octets, recalés sur les sauts de ligne.

    On coupe d'abord à taille * i / n, puis on avance jusqu'au saut de ligne suivant :
    chaque bloc commence donc au début d'une ligne et se termine juste après un "\\n".
    Le bloc suivant commence exactement là où le précédent s'arrête : aucune ligne
    n'est perdue ni comptée deux fois.
    """
    taille = os.path.getsize(chemin)
    bornes = [0]
    with open(chemin, "rb") as fichier:
        for i in range(1, n):
            # Jamais avant la borne précédente (cas d'une ligne plus longue qu'un bloc)
            fichier.seek(max(taille * i // n, bornes[-1]))
            fichier.readline()             # finit la ligne en cours : elle reste au bloc précédent
            bornes.append(fichier.tell())
    bornes.append(taille)
    # Un petit fichier peut donner des blocs vides (deux bornes égales) : on les retire
    return [(debut, fin) for debut, fin in zip(bornes, bornes[1:]) if fin > debut]


def lire_lignes(chemin, debut, fin):
    """Générateur : renvoie une à une les lignes (str) comprises entre les octets debut et fin.

    Le bloc est lu par morceaux de TAILLE_LECTURE octets ; chaque morceau est prolongé
    jusqu'au "\\n" suivant pour ne jamais couper une ligne (ni un caractère UTF-8 :
    l'octet "\\n" n'apparaît jamais au milieu d'un caractère multi-octets).
    errors="replace" : comme en P1, un octet invalide ne fait pas planter la lecture.
    """
    with open(chemin, "rb") as fichier:
        fichier.seek(debut)
        restant = fin - debut
        while restant > 0:
            morceau = fichier.read(min(TAILLE_LECTURE, restant))
            if not morceau:                      # fichier raccourci entre-temps : on s'arrête
                break
            if not morceau.endswith(b"\n") and len(morceau) < restant:
                morceau += fichier.readline()    # finit la ligne coupée (fin est toujours après un "\n")
            restant -= len(morceau)
            lignes = morceau.decode("utf-8", errors="replace").split("\n")
            if lignes[-1] == "":                 # le morceau finit par "\n" : dernier élément vide
                lignes.pop()
            yield from lignes


def analyser_bloc(chemin, debut, fin):
    """Travail d'un worker : analyse son bloc et renvoie ses propres résultats.

    Aucune donnée n'est partagée entre workers : chacun remplit ses Counter
    puis les renvoie au processus principal, qui les fusionne.
    """
    return analyser_lignes(lire_lignes(chemin, debut, fin))


def lire_nombre_workers(texte):
    """Convertit l'argument N en entier >= 1, ou retourne None s'il est invalide."""
    try:
        n = int(texte)
    except ValueError:
        return None
    return n if n >= 1 else None


def main():
    # Vérification des arguments : JOURNAL obligatoire, N optionnel
    if len(sys.argv) not in (2, 3):
        print("Erreur : il faut indiquer le journal à analyser.", file=sys.stderr)
        print("Utilisation : python3 src/analyse_par.py JOURNAL [N]", file=sys.stderr)
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

    # Le temps compte tout le travail parallèle : découpage, création des workers,
    # analyse des blocs et fusion (pour une comparaison honnête avec P1).
    debut = time.perf_counter()
    try:
        blocs = calculer_blocs(chemin, n)
        # Les workers ne partagent aucune donnée : chacun reçoit (chemin, debut, fin)
        # et renvoie ses résultats, que le processus principal fusionne ensuite.
        with Pool(processes=n) as pool:
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


# Obligatoire avec multiprocessing : en mode « spawn » / « forkserver », chaque worker
# réimporte ce fichier ; sans ce test, il relancerait lui-même toute l'analyse.
if __name__ == "__main__":
    sys.exit(main())
