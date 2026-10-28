#!/usr/bin/env python3
"""
tracer_graphique.py — Projet ParaLog (CESI, S3) — Graphique des mesures (P6)

Lit le fichier .csv écrit par mesurer.sh (colonnes version,essai,temps_s),
calcule la médiane et l'accélération de chaque version, les affiche, et
dessine le graphique dans un fichier SVG placé à côté du .csv :
    resultats/mesures_p2_NOM.csv  ->  resultats/graphique_p2_NOM.svg

Pas de matplotlib (bibliothèque standard uniquement) : un SVG est un simple
fichier texte (rectangles, lignes, textes) qu'un navigateur sait afficher
et qu'on peut insérer dans le rapport PDF.

Utilisation (depuis la racine du dépôt) :
    python3 scripts/tracer_graphique.py                                -> resultats/mesures_p2_access.csv
    python3 scripts/tracer_graphique.py resultats/mesures_p2_NOM.csv
"""
import csv
import math
import os
import sys
from statistics import median
from xml.sax.saxutils import escape

# Racine du dépôt, déduite de l'emplacement du script (aucun chemin absolu en dur)
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PAR_DEFAUT = os.path.join(RACINE, "resultats", "mesures_p2_access.csv")

# Dimensions du dessin (en pixels) et couleurs
LARGEUR, HAUTEUR = 960, 440
HAUT, BAS = 90, 350                  # haut et bas des zones de tracé
COULEUR_SEQ = "#7f8c8d"              # gris : version séquentielle
COULEUR_PAR = "#2e6fba"              # bleu : version parallèle
COULEUR_MEILLEUR = "#e67e22"         # orange : meilleure accélération
COULEUR_TEXTE = "#333333"
COULEUR_GRILLE = "#dddddd"


def lire_mesures(chemin):
    """Lit le .csv et retourne {version: [temps des essais]} dans l'ordre du fichier.

    version vaut "seq" (P1) ou un nombre de workers ("1", "2", "4", "8").
    Lève ValueError si le contenu n'a pas le format attendu.
    """
    mesures = {}
    with open(chemin, encoding="utf-8", newline="") as fichier:
        lecteur = csv.DictReader(fichier)
        for ligne in lecteur:
            try:
                version = ligne["version"]
                temps = float(ligne["temps_s"])
                # version : "seq" ou un entier ; temps > 0 (on divise par lui pour l'accélération)
                valide = (version == "seq" or version.isdigit()) and temps > 0
            except (KeyError, TypeError, ValueError, AttributeError):
                valide = False
            if not valide:
                raise ValueError(f"ligne {lecteur.line_num} mal formée (attendu : version,essai,temps_s)")
            mesures.setdefault(version, []).append(temps)
    if "seq" not in mesures:
        raise ValueError("aucune mesure de la version séquentielle (version « seq »)")
    return mesures


def calculer_resume(mesures):
    """Retourne une liste de (version, temps, médiane, accélération), séquentiel en premier.

    Accélération = médiane séquentielle ÷ médiane de la version (comme dans mesurer.sh).
    """
    med_seq = median(mesures["seq"])
    resume = []
    for version, temps in mesures.items():
        med = median(temps)
        resume.append((version, temps, med, med_seq / med))
    # Séquentiel d'abord, puis les workers par nombre croissant
    resume.sort(key=lambda r: -1 if r[0] == "seq" else int(r[0]))
    return resume


# --- Petites fonctions de dessin : chacune renvoie une balise SVG (une chaîne) ---

def texte(x, y, contenu, taille=12, ancre="middle", gras=False, couleur=COULEUR_TEXTE, rotation=0,
          halo=False):
    """Texte centré (ancre="middle"), aligné à gauche ("start") ou à droite ("end").

    halo=True entoure les lettres d'un liseré blanc : le texte reste lisible
    même si une ligne du graphique passe derrière.
    """
    poids = ' font-weight="bold"' if gras else ""
    tourner = f' transform="rotate({rotation} {x:.1f} {y:.1f})"' if rotation else ""
    contour = ' stroke="#ffffff" stroke-width="3" paint-order="stroke"' if halo else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{taille}" text-anchor="{ancre}"'
            f' fill="{couleur}"{poids}{tourner}{contour}>{escape(contenu)}</text>')


def ligne(x1, y1, x2, y2, couleur, epaisseur=1, pointilles=""):
    tirets = f' stroke-dasharray="{pointilles}"' if pointilles else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"'
            f' stroke="{couleur}" stroke-width="{epaisseur}"{tirets}/>')


def rectangle(x, y, largeur, hauteur, couleur):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{largeur:.1f}" height="{hauteur:.1f}" fill="{couleur}"/>'


def cercle(x, y, rayon, couleur):
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rayon}" fill="{couleur}"/>'


def nombre(valeur, decimales):
    """Nombre à la française : virgule décimale (34.534 -> "34,5" avec 1 décimale)."""
    return f"{valeur:.{decimales}f}".replace(".", ",")


def graduation_max(valeur):
    """Choisit un pas « rond » (1, 2, 5, 10...) et le haut de l'axe, pour 4 à 6 graduations."""
    pas = 10 ** math.floor(math.log10(valeur))
    for multiple in (1, 2, 5, 10):
        if valeur / (pas * multiple) <= 5:
            pas *= multiple
            break
    return pas, pas * math.ceil(valeur / pas)


def axe_vertical(gauche, droite, haut_axe, pas, titre):
    """Graduations horizontales (grille) et titre de l'axe vertical d'un panneau."""
    elements = []
    valeur = 0
    while valeur <= haut_axe + 1e-9:
        y = BAS - (BAS - HAUT) * valeur / haut_axe
        elements.append(ligne(gauche, y, droite, y, COULEUR_GRILLE))
        elements.append(texte(gauche - 8, y + 4, nombre(valeur, 0 if pas >= 1 else 1), 11, "end"))
        valeur += pas
    elements.append(texte(gauche - 45, (HAUT + BAS) / 2, titre, 12, rotation=-90))
    elements.append(ligne(gauche, BAS, droite, BAS, COULEUR_TEXTE))
    return elements


def panneau_temps(resume, gauche, droite):
    """Panneau de gauche : un bâton par version (temps médian), les essais en points noirs."""
    pire = max(max(temps) for _, temps, _, _ in resume)
    pas, haut_axe = graduation_max(pire)
    elements = [texte((gauche + droite) / 2, HAUT - 25, "Temps d'analyse (médiane)", 14, gras=True)]
    elements += axe_vertical(gauche, droite, haut_axe, pas, "Temps (s)")
    meilleure = max((acc for v, _, _, acc in resume if v != "seq"), default=None)
    largeur_case = (droite - gauche) / len(resume)
    for i, (version, temps, med, acc) in enumerate(resume):
        centre = gauche + largeur_case * (i + 0.5)
        if version == "seq":
            couleur, etiquette = COULEUR_SEQ, "séquentiel"
        else:
            couleur = COULEUR_MEILLEUR if acc == meilleure else COULEUR_PAR
            etiquette = f"N = {version}"
        largeur_baton = largeur_case * 0.55
        y_med = BAS - (BAS - HAUT) * med / haut_axe
        elements.append(rectangle(centre - largeur_baton / 2, y_med, largeur_baton, BAS - y_med, couleur))
        # Étiquette au-dessus du bâton ET du point le plus haut, pour ne pas les chevaucher
        y_haut = BAS - (BAS - HAUT) * max(temps) / haut_axe
        elements.append(texte(centre, min(y_med, y_haut) - 8, nombre(med, 1) + " s", 11, gras=True, halo=True))
        elements.append(texte(centre, BAS + 18, etiquette, 12))
        # Les essais, légèrement décalés pour ne pas se superposer
        for j, t in enumerate(temps):
            decalage = (j - (len(temps) - 1) / 2) * 7
            elements.append(cercle(centre + decalage, BAS - (BAS - HAUT) * t / haut_axe, 2.5, "#000000"))
    return elements


def panneau_acceleration(resume, gauche, droite):
    """Panneau de droite : accélération mesurée selon N, comparée à l'accélération idéale (= N)."""
    paralleles = [(int(v), acc) for v, _, _, acc in resume if v != "seq"]
    if not paralleles:
        return [texte((gauche + droite) / 2, (HAUT + BAS) / 2, "Aucune mesure parallèle", 14)]
    plus_grand_n = max(n for n, _ in paralleles)
    pas, haut_axe = graduation_max(max(plus_grand_n, max(acc for _, acc in paralleles)))
    elements = [texte((gauche + droite) / 2, HAUT - 25, "Accélération selon le nombre de workers", 14, gras=True)]
    elements += axe_vertical(gauche, droite, haut_axe, pas, "Accélération (temps séq. ÷ temps par.)")

    def position(i, valeur):
        # Les N sont espacés régulièrement (1, 2, 4, 8 : chaque N est le double du précédent)
        x = gauche + (droite - gauche) * (i + 0.5) / len(paralleles)
        return x, BAS - (BAS - HAUT) * valeur / haut_axe

    # Repère « séquentiel = x1 » ; son étiquette est sous la ligne, entre les 2e et 3e points
    _, y_un = position(0, 1)
    elements.append(ligne(gauche, y_un, droite, y_un, COULEUR_SEQ, 1, "2 3"))
    x_etiquette = gauche + (droite - gauche) * min(2, len(paralleles)) / len(paralleles)
    elements.append(texte(x_etiquette, y_un + 14, "séquentiel (x1)", 10, couleur=COULEUR_SEQ, halo=True))
    meilleure = max(acc for _, acc in paralleles)
    for i, (n, acc) in enumerate(paralleles):
        x, y = position(i, acc)
        x_ideal, y_ideal = position(i, n)
        if i > 0:
            elements.append(ligne(*position(i - 1, paralleles[i - 1][0]), x_ideal, y_ideal, COULEUR_SEQ, 2, "6 4"))
            elements.append(ligne(*position(i - 1, paralleles[i - 1][1]), x, y, COULEUR_PAR, 2.5))
        elements.append(cercle(x_ideal, y_ideal, 3, COULEUR_SEQ))
        elements.append(cercle(x, y, 5, COULEUR_MEILLEUR if acc == meilleure else COULEUR_PAR))
        elements.append(texte(x, y - 10, "x" + nombre(acc, 2), 11, gras=True, halo=True))
        elements.append(texte(x, BAS + 18, f"N = {n}", 12))
    # Légende
    elements.append(ligne(gauche + 10, HAUT + 2, gauche + 40, HAUT + 2, COULEUR_PAR, 2.5))
    elements.append(texte(gauche + 46, HAUT + 6, "mesurée", 11, "start"))
    elements.append(ligne(gauche + 10, HAUT + 20, gauche + 40, HAUT + 20, COULEUR_SEQ, 2, "6 4"))
    elements.append(texte(gauche + 46, HAUT + 24, "idéale (= N)", 11, "start"))
    return elements


def dessiner_svg(resume, titre):
    """Assemble les deux panneaux dans un document SVG complet (chaîne)."""
    essais = max(len(temps) for _, temps, _, _ in resume)
    elements = [rectangle(0, 0, LARGEUR, HAUTEUR, "#ffffff"),
                texte(LARGEUR / 2, 28, titre, 16, gras=True)]
    elements += panneau_temps(resume, 80, 450)
    elements += panneau_acceleration(resume, 570, 940)
    elements.append(texte(LARGEUR / 2, HAUTEUR - 30,
                          f"Bâtons : médiane de {essais} essai(s) ; points noirs : chaque essai. "
                          "Orange : meilleure accélération.", 11))
    elements.append(texte(LARGEUR / 2, HAUTEUR - 12,
                          "Accélération = médiane séquentielle ÷ médiane de la version.", 11))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{LARGEUR}" height="{HAUTEUR}"'
            f' viewBox="0 0 {LARGEUR} {HAUTEUR}" font-family="Arial, Helvetica, sans-serif">\n'
            + "\n".join(elements) + "\n</svg>\n")


def chemin_svg(chemin_csv):
    """resultats/mesures_p2_NOM.csv -> resultats/graphique_p2_NOM.svg (même dossier)."""
    dossier, nom = os.path.split(chemin_csv)
    nom = os.path.splitext(nom)[0]
    if nom.startswith("mesures_"):
        nom = "graphique_" + nom[len("mesures_"):]
    else:
        nom = "graphique_" + nom
    return os.path.join(dossier, nom + ".svg")


def main():
    if len(sys.argv) > 2:
        print("Erreur : un seul fichier de mesures à la fois.", file=sys.stderr)
        print("Utilisation : python3 scripts/tracer_graphique.py [MESURES.csv]", file=sys.stderr)
        return 2
    chemin = sys.argv[1] if len(sys.argv) == 2 else CSV_PAR_DEFAUT

    try:
        resume = calculer_resume(lire_mesures(chemin))
    except FileNotFoundError:
        print(f"Erreur : fichier introuvable : {chemin}", file=sys.stderr)
        return 1
    except OSError as erreur:
        print(f"Erreur : impossible de lire {chemin} : {erreur.strerror}", file=sys.stderr)
        return 1
    except ValueError as erreur:
        print(f"Erreur : {chemin} : {erreur}", file=sys.stderr)
        return 1

    print(f"{'Version':<12} {'Médiane (s)':>12} {'Accélération':>13}")
    for version, _, med, acc in resume:
        libelle = "séquentiel" if version == "seq" else f"{version} worker(s)"
        print(f"{libelle:<12} {med:>12.3f} {'x' + format(acc, '.2f'):>13}")

    sortie = chemin_svg(chemin)
    nom_journal = os.path.splitext(os.path.basename(chemin))[0].replace("mesures_p2_", "")
    try:
        with open(sortie, "w", encoding="utf-8") as fichier:
            fichier.write(dessiner_svg(resume, f"ParaLog — mesures de performance P6 ({nom_journal})"))
    except OSError as erreur:
        print(f"Erreur : impossible d'écrire {sortie} : {erreur.strerror}", file=sys.stderr)
        return 1
    print(f"Écrit : {os.path.relpath(sortie)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
