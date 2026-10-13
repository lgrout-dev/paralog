#!/usr/bin/env python3
"""
generer_logs.py — Projet ParaLog (CESI, S3)

Génère un journal d'accès au format Apache « combined », réaliste et reproductible :
la même graine donne exactement le même fichier, sur toutes les machines.

Exemples (depuis la racine du dépôt) :
    python3 scripts/generer_logs.py -o data/access.log    # fichier du projet (~2 Go, 9 millions de lignes)
    python3 scripts/generer_logs.py --lignes 100000 -o data/echantillon_access.log
    python3 scripts/generer_logs.py --lignes 20000 --graine 21 --date 2026-10-05 -o data/access_small.log

Format d'une ligne (champs séparés par des espaces, numérotés comme pour `cut -d' ' -fN`) :
    1 IP   2 -   3 -   4 [date:heure   5 fuseau]   6 "MÉTHODE   7 chemin   8 HTTP/1.1"
    9 code HTTP   10 taille (octets, ou - si vide)   11 "référent"   12+ "navigateur"
"""
import argparse
import datetime as dt
import random
import sys

MOIS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Profil horaire d'une journée (part relative du trafic par heure, 0h → 23h)
PROFIL_HEURES = [2, 1.5, 1, 1, 1, 1.5, 3, 5, 7, 8, 8.5, 8, 7, 7.5, 8, 8, 7.5, 7, 6, 5.5, 5, 4.5, 3.5, 2.5]

METHODES = (["GET", "POST", "HEAD", "PUT"], [88, 10, 1, 1])
CODES = ([200, 304, 301, 302, 404, 403, 500, 503], [82, 6, 2, 2, 5, 1, 1.5, 0.5])

PAGES = (["/", "/index.html", "/contact", "/a-propos", "/connexion", "/panier", "/recherche", "/blog",
          "/aide", "/mentions-legales", "/favicon.ico", "/robots.txt", "/css/style.css", "/js/app.js"]
         + [f"/produits/{i}" for i in range(1, 121)]
         + [f"/blog/article-{i}" for i in range(1, 41)]
         + [f"/api/v1/{r}" for r in ("panier", "stock", "prix", "session", "avis", "commande")]
         + [f"/images/photo-{i}.jpg" for i in range(1, 31)])

REFERENTS = ["-", "https://www.google.fr/", "https://www.bing.com/", "https://www.webnorm.example/",
             "https://www.webnorm.example/produits", "https://www.webnorm.example/blog",
             "https://www.qwant.com/", "https://duckduckgo.com/"]
NAVIGATEURS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:131.0) Gecko/20100101 Firefox/131.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Mobile Safari/537.36",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "curl/8.5.0",
]

# Un robot qui scanne le site à la recherche de failles : il génère beaucoup de 404
SCANNER_IP = "203.0.113.66"
SCANNER_PAGES = ["/wp-login.php", "/wp-admin/", "/.env", "/phpmyadmin/", "/admin.php", "/.git/config", "/xmlrpc.php"]
SCANNER_UA = "Mozilla/5.0 zgrab/0.x"
PART_SCANNER = 0.015

# Plages d'adresses réservées à la documentation ou privées : aucune vraie personne derrière.
def pool_ip(rng, n=6000):
    plages = ["192.0.2.", "198.51.100.", "203.0.113.", "10.20.", "10.42.", "172.16.", "172.20.", "192.168.1.", "192.168.10."]
    ips = set()
    while len(ips) < n:
        p = rng.choice(plages)
        ip = p + (f"{rng.randint(0, 255)}.{rng.randint(1, 254)}" if p.count(".") == 2 else str(rng.randint(1, 254)))
        if ip != SCANNER_IP:
            ips.add(ip)
    return sorted(ips)


def zipf(n, s=1.1):
    return [1 / (k ** s) for k in range(1, n + 1)]


def generer(nb_lignes, graine, jour, sortie):
    rng = random.Random(graine)
    ips = pool_ip(rng)
    rng.shuffle(ips)
    poids_ip = zipf(len(ips), 0.8)
    pages = PAGES[1:]
    rng.shuffle(pages)
    pages = ["/"] + pages            # la page d'accueil reste la plus demandée
    poids_pages = zipf(len(pages), 1.0)
    total_profil = sum(PROFIL_HEURES)
    restants = nb_lignes
    date_txt = f"{jour.day:02d}/{MOIS[jour.month - 1]}/{jour.year}"
    ecrites = 0
    for h, part in enumerate(PROFIL_HEURES):
        n = restants if h == 23 else round(nb_lignes * part / total_profil)
        n = min(n, restants)
        restants -= n
        secondes = sorted(rng.randrange(3600) for _ in range(n))
        # tirages groupés par heure (rapide)
        t_ip = rng.choices(ips, poids_ip, k=n)
        t_page = rng.choices(pages, poids_pages, k=n)
        t_meth = rng.choices(*METHODES, k=n)
        t_code = rng.choices(*CODES, k=n)
        t_ref = rng.choices(REFERENTS, [40, 25, 5, 15, 6, 4, 3, 2], k=n)
        t_ua = rng.choices(NAVIGATEURS, [34, 18, 8, 18, 14, 6, 2], k=n)
        t_scan = [rng.random() < PART_SCANNER for _ in range(n)]
        lignes = []
        for i in range(n):
            s = secondes[i]
            horo = f"[{date_txt}:{h:02d}:{s // 60:02d}:{s % 60:02d} +0200]"
            if t_scan[i]:
                ip, meth, page, code, ua, ref = SCANNER_IP, "GET", rng.choice(SCANNER_PAGES), 404, SCANNER_UA, "-"
            else:
                ip, meth, page, code, ua, ref = t_ip[i], t_meth[i], t_page[i], t_code[i], t_ua[i], t_ref[i]
            if code == 304 or meth == "HEAD":
                taille = "-"
            elif code >= 400:
                taille = str(rng.randint(1000, 5000))
            else:
                taille = str(rng.randint(1000, 60000))
            lignes.append(f'{ip} - - {horo} "{meth} {page} HTTP/1.1" {code} {taille} "{ref}" "{ua}"\n')
        sortie.writelines(lignes)
        ecrites += n
        print(f"\r  {ecrites:>10,} / {nb_lignes:,} lignes".replace(",", " "), end="", file=sys.stderr)
    print(file=sys.stderr)


def main():
    p = argparse.ArgumentParser(description="Génère un journal Apache reproductible (projet ParaLog).")
    p.add_argument("--lignes", type=int, default=9_000_000, help="nombre de lignes (défaut : 9 000 000 ≈ 2 Go)")
    p.add_argument("--graine", type=int, default=2026, help="graine aléatoire (défaut : 2026, celle du projet)")
    p.add_argument("--date", default="2026-10-07", help="jour simulé AAAA-MM-JJ (défaut : 2026-10-07)")
    p.add_argument("-o", "--sortie", default="access.log", help="fichier produit (défaut : access.log)")
    a = p.parse_args()
    jour = dt.date.fromisoformat(a.date)
    print(f"Génération de {a.lignes:,} lignes (graine {a.graine}) dans {a.sortie}…".replace(",", " "), file=sys.stderr)
    with open(a.sortie, "w", encoding="utf-8", newline="\n", buffering=1 << 20) as f:
        generer(a.lignes, a.graine, jour, f)
    print("Terminé.", file=sys.stderr)


if __name__ == "__main__":
    main()
