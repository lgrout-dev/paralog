#!/usr/bin/env python3
"""
demontrer_p4.py — Projet ParaLog (CESI, S3) — Preuve « aucune donnée partagée » (P4)

Lance un vrai Pool avec la fonction analyser_bloc() de la version parallèle (P2)
et montre, à l'exécution, que les workers ne partagent aucune mémoire :
  1. chaque bloc est traité dans un processus distinct (PID différent du principal) ;
  2. une variable globale modifiée par les workers reste à 0 dans le processus
     principal : chaque processus a sa propre copie, rien n'est partagé ;
  3. la somme des lignes des blocs = le total, et la fusion = la version séquentielle.

Utilisation (depuis la racine du dépôt) :
    python3 scripts/demontrer_p4.py                          -> échantillon, 4 workers
    python3 scripts/demontrer_p4.py data/echantillon_access.log 8
Code de retour : 0 si la démonstration est vérifiée, 1 sinon (ou fichier absent), 2 si mauvaise utilisation.
"""
import os
import sys
from multiprocessing import Pool

# Le dossier src/ est trouvé à partir de l'emplacement du script (aucun chemin absolu)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from analyse_commun import analyser_lignes, fusionner
from analyse_par import analyser_bloc, calculer_blocs, lire_nombre_workers

# Variable globale volontairement modifiée par les workers.
# Si la mémoire était partagée, le processus principal verrait la somme de leurs ajouts.
LIGNES_VUES = 0


def tache(chemin, debut, fin):
    """Travail d'un worker : la vraie analyse de P2, plus quelques informations pour la preuve."""
    global LIGNES_VUES
    res = analyser_bloc(chemin, debut, fin)
    lignes = res["analysees"] + res["ignorees"]
    LIGNES_VUES += lignes            # modifie la copie de CE processus seulement
    return os.getpid(), debut, fin, lignes, LIGNES_VUES, res


def main():
    if len(sys.argv) > 3:
        print("Erreur : trop d'arguments.", file=sys.stderr)
        print("Utilisation : python3 scripts/demontrer_p4.py [JOURNAL] [N]", file=sys.stderr)
        return 2
    chemin = sys.argv[1] if len(sys.argv) >= 2 else "data/echantillon_access.log"
    n = lire_nombre_workers(sys.argv[2]) if len(sys.argv) == 3 else 4
    if n is None:
        print(f"Erreur : N doit être un entier supérieur ou égal à 1 (reçu : {sys.argv[2]}).",
              file=sys.stderr)
        return 2

    try:
        blocs = calculer_blocs(chemin, n)
        with Pool(processes=n) as pool:
            retours = pool.starmap(tache, [(chemin, d, f) for d, f in blocs])
        # Référence : analyse séquentielle, comme en P1
        with open(chemin, encoding="utf-8", errors="replace") as fichier:
            reference = analyser_lignes(fichier)
    except FileNotFoundError:
        print(f"Erreur : fichier introuvable : {chemin}", file=sys.stderr)
        return 1
    except OSError as erreur:
        print(f"Erreur : impossible de lire {chemin} : {erreur.strerror}", file=sys.stderr)
        return 1

    pid_principal = os.getpid()
    print(f"Journal : {chemin}, {n} workers, processus principal : PID {pid_principal}")
    print()
    print(f"{'PID worker':>10}  {'bloc (octets)':>23}  {'lignes du bloc':>14}  {'LIGNES_VUES dans ce worker':>26}")
    for pid, debut, fin, lignes, vues, _ in retours:
        print(f"{pid:>10}  {debut:>11}-{fin:<11}  {lignes:>14}  {vues:>26}")
    print()

    pids = {r[0] for r in retours}
    total_blocs = sum(r[3] for r in retours)
    total_reference = reference["analysees"] + reference["ignorees"]
    fusion = fusionner(r[5] for r in retours)

    # Chaque vérification : (description, résultat)
    verifications = [
        (f"Blocs traités hors du processus principal : PID des workers {sorted(pids)}, "
         f"principal {pid_principal}", pid_principal not in pids),
        (f"LIGNES_VUES dans le processus principal = {LIGNES_VUES} (attendu : 0, "
         f"car chaque worker modifie sa propre copie)", LIGNES_VUES == 0),
        (f"Somme des lignes des blocs = {total_blocs}, total séquentiel = {total_reference}",
         total_blocs == total_reference),
        ("Fusion des résultats des workers = résultat séquentiel", fusion == reference),
    ]
    for texte, ok in verifications:
        print(f"[{'OK' if ok else 'ÉCHEC'}] {texte}")

    if len(pids) < len(retours) and pid_principal not in pids:
        print("Remarque : un même worker a traité plusieurs blocs ; sa valeur de LIGNES_VUES "
              "cumule ses blocs, ce qui confirme que la variable est propre à chaque processus.")

    if all(ok for _, ok in verifications):
        print("Conclusion : aucune donnée partagée entre les workers, donc aucune section critique.")
        return 0
    print("Conclusion : ÉCHEC de la démonstration.", file=sys.stderr)
    return 1


# Obligatoire avec multiprocessing (voir analyse_par.py)
if __name__ == "__main__":
    sys.exit(main())
