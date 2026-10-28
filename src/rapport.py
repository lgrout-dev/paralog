"""
rapport.py — Projet ParaLog (CESI, S3)

Mise en forme du rapport, partagée entre les versions séquentielle et parallèle
pour qu'elles produisent exactement le même texte.
Le temps d'analyse est volontairement sur la DERNIÈRE ligne : c'est la seule
qui diffère entre deux exécutions, ce qui facilite la comparaison avec diff.
"""

TAILLE_TOP = 10


def top(compteur, n=TAILLE_TOP):
    """Retourne les n éléments les plus fréquents, triés de façon déterministe :
    nombre décroissant, puis clé croissante en cas d'égalité.
    (Counter.most_common() laisse les ex aequo dans l'ordre où les clés ont été vues
    pour la première fois : cet ordre change si le fichier est lu par blocs en parallèle.)
    """
    return sorted(compteur.items(), key=lambda paire: (-paire[1], paire[0]))[:n]


def formater_rapport(resultats, chemin, duree):
    """Construit le texte du rapport.

    resultats : dictionnaire retourné par analyser_lignes() ou fusionner()
    chemin    : nom du journal analysé (affiché tel quel)
    duree     : temps d'analyse en secondes
    """
    lignes = []
    lignes.append("=== Rapport ParaLog ===")
    lignes.append(f"Journal analysé : {chemin}")
    lignes.append(f"Lignes analysées : {resultats['analysees']}")
    lignes.append(f"Lignes ignorées (mal formées) : {resultats['ignorees']}")

    # 1. Requêtes par code HTTP, triées par code
    lignes.append("")
    lignes.append("--- 1. Requêtes par code HTTP ---")
    for code in sorted(resultats["codes"]):
        lignes.append(f"{code} : {resultats['codes'][code]}")

    # 2. Top 10 des adresses IP
    lignes.append("")
    lignes.append(f"--- 2. Top {TAILLE_TOP} des adresses IP ---")
    for rang, (ip, nb) in enumerate(top(resultats["ips"]), start=1):
        lignes.append(f"{rang:2d}. {ip:<18} {nb}")

    # 3. Top 10 des pages
    lignes.append("")
    lignes.append(f"--- 3. Top {TAILLE_TOP} des pages ---")
    for rang, (page, nb) in enumerate(top(resultats["pages"]), start=1):
        lignes.append(f"{rang:2d}. {page:<30} {nb}")

    # 4. Requêtes par heure : toujours 24 lignes (un Counter renvoie 0 pour une heure absente)
    lignes.append("")
    lignes.append("--- 4. Requêtes par heure ---")
    for heure in range(24):
        lignes.append(f"{heure:02d}h : {resultats['heures'][heure]}")

    lignes.append("")
    lignes.append(f"Temps d'analyse : {duree:.3f} s")
    return "\n".join(lignes) + "\n"
