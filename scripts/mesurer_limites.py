#!/usr/bin/env python3
"""
mesurer_limites.py — Projet ParaLog (CESI, S3) — Analyse des limites (P7)

Décompose le temps de la version parallèle (P2) en phases, pour montrer
d'où vient l'écart entre l'accélération mesurée et l'accélération idéale (= N) :
  1. lecture du disque : lecture seule du journal, puis lecture + décodage en lignes
     (sans analyse), dans le processus principal ;
  2. coût de création des processus : un Pool de N workers créé puis arrêté sans travail ;
  3. nombre de cœurs : pour chaque worker, temps écoulé (horloge) et temps de calcul (CPU) ;
     si un worker attend un cœur libre, son temps écoulé dépasse son temps CPU ;
  4. partie non parallélisable : découpage, surcoût du Pool, renvoi des résultats, fusion.

Les vraies fonctions de P2 (calculer_blocs, lire_lignes, analyser_bloc, fusionner)
sont appelées sans être modifiées.

Utilisation (depuis la racine du dépôt) :
    python3 scripts/mesurer_limites.py                                -> échantillon, N = 1 2 4 8
    python3 scripts/mesurer_limites.py data/echantillon_access.log 2 4
Code de retour : 0 = OK, 1 = fichier absent ou illisible, 2 = mauvaise utilisation.
"""
import os
import pickle
import sys
import time
from multiprocessing import Pool

# Le dossier src/ est trouvé à partir de l'emplacement du script (aucun chemin absolu)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from analyse_commun import fusionner
from analyse_par import TAILLE_LECTURE, analyser_bloc, calculer_blocs, lire_lignes, lire_nombre_workers


def lire_sans_analyser(chemin):
    """Lit tout le fichier par morceaux de TAILLE_LECTURE octets, sans rien en faire."""
    octets = 0
    with open(chemin, "rb") as fichier:
        while True:
            morceau = fichier.read(TAILLE_LECTURE)
            if not morceau:
                return octets
            octets += len(morceau)


def tache_vide(_):
    """Tâche qui ne fait rien : sert à mesurer le seul coût des workers."""
    return os.getpid()


def tache_mesuree(chemin, debut, fin):
    """Travail d'un worker : la vraie analyse de P2, chronomètrée dans le worker.

    perf_counter() mesure le temps écoulé (horloge murale) ;
    process_time() mesure le temps de calcul réellement donné à CE processus par le noyau.
    """
    debut_horloge, debut_cpu = time.perf_counter(), time.process_time()
    res = analyser_bloc(chemin, debut, fin)
    horloge = time.perf_counter() - debut_horloge
    cpu = time.process_time() - debut_cpu
    # Taille du résultat une fois sérialisé : c'est ce que le Pool recopie vers le principal
    return os.getpid(), horloge, cpu, len(pickle.dumps(res)), res


def mesurer_n(chemin, n):
    """Mesure chaque phase de P2 avec n workers et retourne un dictionnaire de temps."""
    m = {}

    # Coût fixe : créer n workers, leur donner une tâche vide chacun, les arrêter
    t = time.perf_counter()
    with Pool(processes=n) as pool:
        pool.map(tache_vide, range(n), chunksize=1)
    m["pool_vide"] = time.perf_counter() - t

    # La vraie exécution de P2, découpée en phases (même enchaînement que main() de analyse_par.py)
    t0 = time.perf_counter()
    blocs = calculer_blocs(chemin, n)
    t1 = time.perf_counter()
    with Pool(processes=n) as pool:
        retours = pool.starmap(tache_mesuree, [(chemin, d, f) for d, f in blocs])
    t2 = time.perf_counter()
    resultats = fusionner(r[4] for r in retours)
    t3 = time.perf_counter()

    m["decoupage"] = t1 - t0
    m["phase_parallele"] = t2 - t1
    m["fusion"] = t3 - t2
    m["total"] = t3 - t0
    m["workers"] = [(r[0], r[1], r[2]) for r in retours]     # (PID, horloge, CPU)
    m["max_worker"] = max(r[1] for r in retours)
    m["somme_cpu"] = sum(r[2] for r in retours)
    m["octets_renvoyes"] = sum(r[3] for r in retours)
    # Ce qui, dans la phase parallèle, n'est pas le travail du worker le plus long :
    # démarrage des processus, envoi des tâches, renvoi (pickle) des résultats, arrêt
    m["surcout_pool"] = m["phase_parallele"] - m["max_worker"]
    m["non_parallele"] = m["decoupage"] + m["surcout_pool"] + m["fusion"]
    m["lignes"] = resultats["analysees"] + resultats["ignorees"]
    return m


def main():
    chemin = sys.argv[1] if len(sys.argv) >= 2 else "data/echantillon_access.log"
    liste_n = []
    for texte in sys.argv[2:] or ["1", "2", "4", "8"]:
        n = lire_nombre_workers(texte)
        if n is None:
            print(f"Erreur : N doit être un entier supérieur ou égal à 1 (reçu : {texte}).",
                  file=sys.stderr)
            print("Utilisation : python3 scripts/mesurer_limites.py [JOURNAL] [N ...]", file=sys.stderr)
            return 2
        liste_n.append(n)

    try:
        # 1. Lecture du disque, dans le processus principal (aucun worker)
        t = time.perf_counter()
        octets = lire_sans_analyser(chemin)
        lecture_seule = time.perf_counter() - t
        t = time.perf_counter()
        nb_lignes = sum(1 for _ in lire_lignes(chemin, 0, octets))
        lecture_decodage = time.perf_counter() - t
        # 2 à 4. Phases de P2 pour chaque N
        mesures = [(n, mesurer_n(chemin, n)) for n in liste_n]
    except FileNotFoundError:
        print(f"Erreur : fichier introuvable : {chemin}", file=sys.stderr)
        return 1
    except OSError as erreur:
        print(f"Erreur : impossible de lire {chemin} : {erreur.strerror}", file=sys.stderr)
        return 1

    print(f"=== Limites de la version parallèle (P7) — {chemin} ===")
    print(f"Fichier : {nb_lignes} lignes, {octets / 1e6:.1f} Mo ; "
          f"cœurs logiques vus par Python : {os.cpu_count()}")
    print()
    print("1. Lecture du disque (processus principal, sans analyse)")
    print(f"   lecture seule (morceaux de 16 Mo)      : {lecture_seule:8.3f} s  "
          f"({octets / 1e6 / max(lecture_seule, 1e-9):.0f} Mo/s)")
    print(f"   lecture + décodage + découpage lignes  : {lecture_decodage:8.3f} s")
    print()

    print("2 à 4. Phases de P2 selon N (temps en secondes)")
    print(f"{'N':>3} {'Pool vide':>10} {'découpage':>10} {'phase par.':>11} {'worker max':>11} "
          f"{'surcoût':>8} {'fusion':>8} {'total':>8} {'CPU total':>10} {'renvoyé':>9} {'non par.':>9}")
    for n, m in mesures:
        print(f"{n:>3} {m['pool_vide']:>10.3f} {m['decoupage']:>10.3f} {m['phase_parallele']:>11.3f} "
              f"{m['max_worker']:>11.3f} {m['surcout_pool']:>8.3f} {m['fusion']:>8.3f} "
              f"{m['total']:>8.3f} {m['somme_cpu']:>10.3f} {m['octets_renvoyes'] / 1e3:>7.0f}ko "
              f"{100 * m['non_parallele'] / m['total']:>8.1f}%")
    print()

    print("3. Détail par worker : temps écoulé (horloge) et temps de calcul (CPU)")
    for n, m in mesures:
        details = ", ".join(f"{h:.2f}/{c:.2f}" for _, h, c in m["workers"])
        print(f"   N = {n} : {details}")
    print()

    print("Légende :")
    print("  Pool vide  : créer N workers, leur donner une tâche vide, les arrêter (coût fixe)")
    print("  phase par. : Pool + analyse des blocs + renvoi des résultats ; worker max = bloc le plus long")
    print("  surcoût    : phase par. - worker max (démarrage, envoi, pickle des résultats, arrêt)")
    print("  CPU total  : somme des temps de calcul des workers (augmente si les cœurs sont partagés)")
    print("  renvoyé    : taille des résultats sérialisés (pickle) recopiés vers le principal")
    print("  non par.   : (découpage + surcoût + fusion) / total")

    # Contrôle : chaque N a bien analysé toutes les lignes
    if any(m["lignes"] != nb_lignes for _, m in mesures):
        print("Erreur : nombre de lignes différent selon N.", file=sys.stderr)
        return 1
    return 0


# Obligatoire avec multiprocessing (voir analyse_par.py)
if __name__ == "__main__":
    sys.exit(main())
