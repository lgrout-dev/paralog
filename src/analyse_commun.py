"""
analyse_commun.py — Projet ParaLog (CESI, S3)

Fonctions d'analyse partagées entre la version séquentielle (P1)
et la future version parallèle (P2).

Format d'une ligne (champs séparés par des espaces, numérotés comme `cut -d' ' -fN`) :
    1 IP   2 -   3 -   4 [date:heure   5 fuseau]   6 "MÉTHODE   7 chemin   8 HTTP/1.1"
    9 code HTTP   10 taille   11 "référent"   12+ "navigateur"

Une ligne est considérée comme MAL FORMÉE (comptée puis ignorée) si l'un des champs
essentiels (adresse IP, date/heure, code HTTP) est incohérent (d’après la réponse de l’encadrant) :
    - elle a moins de 9 champs ;
    - l'IP (champ 1) n'a pas la forme de 4 nombres séparés par des points ;
    - le champ 4 n'a pas la forme [jj/Mmm/aaaa:HH:... avec HH entre 00 et 23 ;
    - le code HTTP (champ 9) n'est pas un nombre à 3 chiffres.
Un décalage des champs (ex. requête vide "-") est détecté par le contrôle du code HTTP.
Les contrôles restent volontairement simples : la priorité est le temps d'analyse.
"""
from collections import Counter


def analyser_ligne(ligne):
    """Extrait (ip, page, code, heure) d'une ligne, ou retourne None si elle est mal formée.

    code et heure sont des entiers (ex. 200 et 14), ip et page des chaînes.
    """
    # On ne découpe que les 9 premiers champs : le reste (référent, navigateur)
    # ne nous sert pas et contient des espaces. split() sans argument découpe
    # sur les suites d'espaces, comme awk.
    champs = ligne.split(None, 9)
    if len(champs) < 9:
        return None

    ip = champs[0]
    date = champs[3]          # ex. "[07/Oct/2026:14:05:32"
    page = champs[6]          # ex. "/produits/118"
    code = champs[8]          # ex. "200"

    # IP : exactement 3 points, et uniquement des chiffres une fois les points retirés
    if ip.count(".") != 3 or not ip.replace(".", "").isdigit():
        return None

    # Code HTTP : exactement 3 chiffres
    if len(code) != 3 or not code.isdigit():
        return None

    # Date : "[" au début, puis l'heure entre le 1er et le 2e ":"
    morceaux = date.split(":")
    if not date.startswith("[") or len(morceaux) < 3:
        return None
    heure = morceaux[1]
    if len(heure) != 2 or not heure.isdigit() or int(heure) > 23:
        return None

    return ip, page, int(code), int(heure)


def resultats_vides():
    """Crée une structure de résultats vide (point de départ d'une analyse ou d'une fusion)."""
    return {
        "codes": Counter(),    # code HTTP -> nombre de requêtes
        "ips": Counter(),      # adresse IP -> nombre de requêtes
        "pages": Counter(),    # page -> nombre de requêtes
        "heures": Counter(),   # heure (0 à 23) -> nombre de requêtes
        "analysees": 0,        # lignes valides
        "ignorees": 0,         # lignes mal formées
    }


def analyser_lignes(lignes):
    """Analyse un itérable de lignes (fichier ouvert, liste, bloc...) et retourne les résultats.

    Le résultat est un dictionnaire de Counter et de compteurs (voir resultats_vides()).
    Les résultats de plusieurs appels peuvent être additionnés avec fusionner().
    """
    res = resultats_vides()
    # Variables locales : accès plus rapide que res["..."] dans la boucle
    codes, ips, pages, heures = res["codes"], res["ips"], res["pages"], res["heures"]
    analysees = 0
    ignorees = 0

    for ligne in lignes:
        infos = analyser_ligne(ligne)
        if infos is None:
            ignorees += 1
            continue
        ip, page, code, heure = infos
        codes[code] += 1
        ips[ip] += 1
        pages[page] += 1
        heures[heure] += 1
        analysees += 1

    res["analysees"] = analysees
    res["ignorees"] = ignorees
    return res


def fusionner(liste_resultats):
    """Additionne plusieurs résultats (ex. ceux des workers en P2) en un seul."""
    total = resultats_vides()
    for res in liste_resultats:
        for cle in ("codes", "ips", "pages", "heures"):
            total[cle].update(res[cle])   # update() additionne les comptes
        total["analysees"] += res["analysees"]
        total["ignorees"] += res["ignorees"]
    return total
