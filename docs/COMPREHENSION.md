# ParaLog — Document de compréhension

Ce document explique, point par point, **ce qui était demandé**, **ce qui a été fait** et **pourquoi**.
Il est mis à jour à chaque changement du projet (voir le [journal des modifications](#journal-des-modifications) en bas).

Le `README.md` à la racine est celui du kit fourni par l'école : on ne le modifie pas.

Ce document est **versionné** depuis le 28/10 (commit `59fbaf6`, retiré du `.gitignore`) ; il était auparavant local.

---

## Sommaire

1. [Le projet en bref](#1-le-projet-en-bref)
2. [Organisation du dépôt](#2-organisation-du-dépôt)
3. [Le format d'une ligne de journal](#3-le-format-dune-ligne-de-journal)
4. [P1 — Version séquentielle](#4-p1--version-séquentielle)
5. [Mesures de performance](#5-mesures-de-performance)
6. [P2 — Version parallèle](#6-p2--version-parallèle)
7. [P4 / P5 — Section critique et interblocage](#7-p4--p5--section-critique-et-interblocage)
8. [Scripts Bash A2 à A8 (installation, droits, lancement, contrôle, nettoyage, archivage)](#8-scripts-bash-a2-à-a8)
9. [A6 — Schéma en couches et appels système](#9-a6--schéma-en-couches-et-appels-système)
10. [Dossier d'architecture (PDF)](#10-dossier-darchitecture-pdf)
11. [P7 — Analyse des limites](#11-p7--analyse-des-limites)
12. [Rapport de performance (PDF)](#12-rapport-de-performance-pdf)
13. [P8 — Processus ou threads ?](#13-p8--processus-ou-threads-)
14. [Prochaines étapes](#14-prochaines-étapes)
15. [Journal des modifications](#journal-des-modifications)

---

## 1. Le projet en bref

ParaLog est un outil Python qui lit un journal d'accès Apache (format *combined*) et écrit un rapport texte.
Le journal complet (`data/access.log`) fait **9 millions de lignes, soit environ 1,9 Go**.

Le projet se déroule en deux étapes :

| Étape | Objectif | État |
| --- | --- | --- |
| **P1** | Version séquentielle : un seul processus lit tout le fichier. Elle sert de **référence** pour les résultats et pour le temps. | Faite (temps de référence : 59,8 s) |
| **P2** | Version parallèle : plusieurs processus analysent chacun un bloc du fichier. Elle doit produire **exactement le même rapport**, plus vite. | Faite, identique à P1 sur l'échantillon et sur `access.log` (N = 1, 2, 4, 8). Meilleure accélération : **x1,44 avec 2 workers** (Mac, 2 cœurs physiques). P6 complète : tableau + graphique `resultats/graphique_p2_access.svg` |
| **P4 / P5** | Aucune donnée partagée (pas de section critique), pas d'interblocage (Coffman). | Faites le 26/10 : `docs/concurrence_P4_P5.md` + preuve `scripts/demontrer_p4.py` (voir [section 7](#7-p4--p5--section-critique-et-interblocage)) |
| **A2–A5, A7, A8** | Scripts Bash : installation, droits et groupe, lancement, chaîne de contrôle, nettoyage, archivage. | Faits le 27/10, testés dans la VM Ubuntu (voir [section 8](#8-scripts-bash-a2-à-a8)) |
| **A6** | Schéma en couches avec au moins deux appels système. | Fait le 27/10 : `docs/schema_A6.md` + `.svg`, appels relevés avec `strace` par `scripts/tracer_appels.sh` (voir [section 9](#9-a6--schéma-en-couches-et-appels-système)) |
| **P7** | Expliquer pourquoi le gain n'est pas proportionnel à N (cœurs, création des processus, disque, partie non parallélisable). | Fait le 27/10 : `docs/limites_P7.md` + mesure de chaque cause par `scripts/mesurer_limites.py` → `resultats/limites_access.txt` (voir [section 11](#11-p7--analyse-des-limites)) |
| **P8** (Attendu) | Mesurer la même analyse avec des threads puis avec des processus, expliquer l'écart. | Fait le 28/10 sur le PC (Ryzen 8 cœurs, WSL) : `src/analyse_threads.py`, `scripts/mesurer_p8.sh`, `docs/threads_P8.md`. 8 threads : x0,84, 0,97 cœur occupé (GIL) ; 8 processus : x4,34, 7,09 cœurs (voir [section 13](#13-p8--processus-ou-threads-)). Mesure Mac à faire |
| **Dossier d'architecture** | Livrable PDF (10 pages max) : arborescence commentée (A1), schéma (A6), droits (A3), mode d'emploi des scripts. | Fait le 27/10 : `docs/dossier_architecture.pdf` (10 pages depuis l'ajout de `mesurer_limites.py`), source `.html`, produit par `scripts/generer_pdf.sh` (voir [section 10](#10-dossier-darchitecture-pdf)). Page de garde à compléter |
| **Rapport de performance** | Livrable PDF (6 pages max) : code, test, tableau et graphique des temps, analyse (P1 à P10). | Fait le 27/10 : `docs/rapport_performance.pdf` (6 pages), source `.html`, `bash scripts/generer_pdf.sh rapport_performance` (voir [section 12](#12-rapport-de-performance-pdf)). Page de garde à compléter |

Contraintes générales : Python 3.8+, bibliothèque standard uniquement, aucun chemin absolu propre à une machine, `data/access.log` jamais versionné.

---

## 2. Organisation du dépôt

```
paralog/
├── README.md                    kit de l'école (ne pas modifier)
├── .gitignore                   exclut access.log, __pycache__/, les rapports de lancer.sh,
│                                les archives .tar.gz, les sources et PDF des livrables
├── data/
│   ├── echantillon_access.log   100 000 lignes (~20 Mo), versionné, pour tester vite
│   └── access.log               9 M lignes (~1,9 Go), généré, NON versionné
├── scripts/
│   ├── generer_logs.py          génère access.log (reproductible, graine 2026)
│   ├── verifier_environnement.sh
│   ├── installer.sh             installation : prérequis, arborescence, groupe, droits (A2, A3)
│   ├── lancer.sh                lance P2 avec N workers, rapport horodaté (A4)
│   ├── controle.sh              chaîne cut | sort | uniq -c : indicateurs 1 et 2 (A5)
│   ├── nettoyer.sh              supprime temporaires et vieux rapports (A7)
│   ├── archiver.sh              archive .tar.gz de resultats/ en 600 (A8)
│   ├── tester_p2.sh             compare P1 et P2 (N = 1, 2, 4, 8) avec diff (P3)
│   ├── mesurer.sh               3 essais P1 + P2, médianes et accélération (P6)
│   ├── tracer_graphique.py      graphique SVG des mesures (P6), sans matplotlib
│   ├── demontrer_p4.py          preuve « aucune donnée partagée » à l'exécution (P4)
│   ├── mesurer_limites.py       décompose le temps de P2 cause par cause (P7)
│   ├── mesurer_p8.sh            threads vs processus (N = 1, 2, 4, 8), 3 essais, cœurs occupés (P8)
│   ├── tracer_appels.sh         relevé strace des appels système du schéma (A6, Linux)
│   └── generer_pdf.sh [NOM]     imprime un livrable en PDF (Chrome headless) : dossier d'architecture
│                                par défaut, ou rapport_performance ; NON versionné
├── src/
│   ├── analyse_commun.py        analyse des lignes (partagé P1 / P2)
│   ├── rapport.py               mise en forme du rapport (partagé P1 / P2)
│   ├── analyse_seq.py           programme principal P1
│   ├── analyse_par.py           programme principal P2 (parallèle, processus)
│   └── analyse_threads.py       même analyse avec des threads (P8), réutilise P2
├── docs/
│   ├── COMPREHENSION.md         ce document (versionné depuis le 28/10)
│   ├── dossier_architecture.html   source du dossier d'architecture (NON versionné)
│   ├── dossier_architecture.pdf    le livrable PDF, 10 pages (NON versionné)
│   ├── rapport_performance.html    source du rapport de performance (NON versionné)
│   ├── rapport_performance.pdf     le livrable PDF, 6 pages (NON versionné)
│   ├── concurrence_P4_P5.md     rédaction P4 / P5 pour le rapport de performance (versionné)
│   ├── limites_P7.md            rédaction P7 (limites de l'accélération) pour le rapport de performance (versionné)
│   ├── threads_P8.md            rédaction P8 (threads vs processus, GIL) pour le rapport de performance (versionné)
│   ├── droits_A3.md             groupe, tableau des droits, preuve (dossier d'architecture, versionné)
│   ├── schema_A6.md             schéma en couches + appels système relevés (versionné)
│   └── schema_A6.svg            le même schéma dessiné, pour le PDF (versionné)
├── resultats/                   rapports et mesures de temps
│   ├── rapport_seq.txt          rapport P1 de référence (access.log)
│   ├── controle_echantillon_access.txt   sortie de controle.sh (A5)
│   ├── rapport_AAAAMMJJ_HHMMSS_*.txt     rapports de lancer.sh (NON versionnés)
│   ├── mesures_p1.txt           3 temps P1 + médiane
│   ├── mesures_p2_access.txt/.csv   mesures P6 : P1 + P2 (N = 1, 2, 4, 8), 3 essais, médianes, accélération
│   ├── graphique_p2_access.svg  graphique P6 (temps médian + accélération selon N)
│   ├── limites_access.txt       sortie de mesurer_limites.py sur access.log (P7)
│   └── mesures_p8_access_linux.txt/.csv   mesures P8 sur le PC (WSL) ; _macos.* pour le Mac
└── archives/                    archives de archiver.sh (700, NON versionnées)
```

Toutes les commandes se lancent **depuis la racine du dépôt**.

---

## 3. Le format d'une ligne de journal

Exemple :

```
10.42.213.80 - - [07/Oct/2026:14:05:32 +0200] "GET /produits/118 HTTP/1.1" 200 45504 "https://www.google.fr/" "Mozilla/5.0 (...)"
```

Champs numérotés comme pour `cut -d' ' -fN` :

| N° | Contenu | Exemple | Utilisé pour |
| --- | --- | --- | --- |
| 1 | Adresse IP | `10.42.213.80` | Top 10 IP |
| 4 | Date et heure | `[07/Oct/2026:14:05:32` | Requêtes par heure (entre le 1er et le 2e `:`) |
| 6 | Méthode | `"GET` | — |
| 7 | Page | `/produits/118` | Top 10 pages |
| 8 | Protocole | `HTTP/1.1"` | — |
| 9 | Code HTTP | `200` | Requêtes par code |
| 10 | Taille | `45504` | — |
| 11+ | Référent, navigateur | … | — |

**Point important :** le navigateur contient des espaces, donc le nombre total de champs varie (de 12 à 24 dans l'échantillon).
Seuls les 9 premiers champs ont une position fiable, et ce sont justement ceux dont on a besoin.

---

## 4. P1 — Version séquentielle

### 4.1 Ce qui était demandé

| # | Demande | Fait | Où |
| --- | --- | --- | --- |
| 1 | `python3 src/analyse_seq.py JOURNAL` écrit un rapport sur la sortie standard | ✅ | `analyse_seq.py` |
| 2 | Nombre de requêtes par code HTTP, tous les codes présents, triés par code | ✅ | `rapport.py` |
| 3 | Top 10 des adresses IP avec leur nombre de requêtes | ✅ | `rapport.py` |
| 4 | Top 10 des pages avec leur nombre de requêtes | ✅ | `rapport.py` |
| 5 | Requêtes par heure : exactement 24 lignes (00h à 23h), même à 0 | ✅ | `rapport.py` |
| 6 | Afficher les lignes analysées, les lignes ignorées et le temps d'analyse | ✅ | `rapport.py`, `analyse_seq.py` |
| 7 | Architecture réutilisable pour P2 (3 fichiers, Counter additionnables) | ✅ | les 3 fichiers |
| 8 | Lecture ligne par ligne (jamais `f.read()`), avec `errors="replace"` | ✅ | `analyse_seq.py` |
| 9 | Tri déterministe des tops : nombre décroissant, puis clé croissante | ✅ | `rapport.py` → `top()` |
| 10 | Lignes mal formées comptées et ignorées, sans arrêter le programme | ✅ | `analyse_commun.py` |
| 11 | Argument manquant ou fichier introuvable : message sur stderr, code de retour ≠ 0 | ✅ | `analyse_seq.py` |
| 12 | Code commenté en français, simple et lisible | ✅ | tous |
| 13 | Ne pas toucher à `data/access.log`, vérifier qu'il est exclu par `.gitignore` | ✅ | vérifié avec `git check-ignore` |
| 14 | Mesurer le temps sur le fichier complet (9 M lignes) | ✅ 3 essais, médiane 59,849 s | voir [section 5](#5-mesures-de-performance) |

### 4.2 L'architecture et pourquoi

```
analyse_seq.py  ──►  analyse_commun.py   (analyser une ligne, compter, fusionner)
      │
      └─────────►  rapport.py          (mettre en forme)

analyse_par.py  ──►  les deux mêmes modules (voir section 6)
```

**Idée directrice :** entre P1 et P2, seule la façon de *lire* le fichier change.
Si les deux versions partagent l'analyse d'une ligne et la mise en forme, une différence entre leurs rapports ne peut venir que du découpage en blocs. C'est beaucoup plus simple à déboguer.

### 4.3 Ce qui a été fait, fichier par fichier

#### `src/analyse_commun.py`

**`analyser_ligne(ligne)`** retourne `(ip, page, code, heure)`, ou `None` si la ligne est mal formée.

- `ligne.split(None, 9)` :
  - `None` découpe sur les suites d'espaces, comme awk, et ignore le `\n` de fin ;
  - `9` arrête le découpage après 9 coupures. On n'a pas besoin du référent ni du navigateur, et sur 9 millions de lignes, ça fait gagner du temps.
- Le code et l'heure sont convertis en entiers. Ça permet de trier les codes numériquement et d'afficher l'heure avec `02d`.
- Retourner `None` laisse l'appelant décider quoi faire : ici, compter la ligne comme ignorée et continuer.

**`analyser_lignes(lignes)`** parcourt n'importe quel itérable (fichier ouvert, liste, bloc de P2) et retourne un dictionnaire :

```python
{"codes": Counter, "ips": Counter, "pages": Counter, "heures": Counter,
 "analysees": int, "ignorees": int}
```

- Un `Counter` est un dictionnaire qui renvoie 0 pour une clé absente : `codes[code] += 1` fonctionne sans initialisation.
- Les Counter sont recopiés dans des variables locales avant la boucle. On évite ainsi une recherche dans le dictionnaire à chaque ligne.
- Le dictionnaire de résultats est simple, et `multiprocessing` sait l'envoyer d'un processus à l'autre : c'est ce que renvoie chaque worker en P2.

**`fusionner(liste_resultats)`** additionne plusieurs résultats en un seul. C'est elle qui regroupe les résultats des workers en P2 (`analyse_par.py`).

- On utilise `update()` plutôt que `+`, parce que `+` supprime silencieusement les comptes nuls.
- Testée : analyser l'échantillon en 2 morceaux puis fusionner donne exactement le même résultat qu'une analyse d'un seul tenant.

#### `src/rapport.py`

- **`top(compteur, n=10)`** trie selon la clé `(-nombre, clé)` : le plus grand nombre d'abord, puis l'ordre alphabétique en cas d'égalité.
  - *Pourquoi pas `Counter.most_common()` ?* En cas d'égalité, il garde l'ordre dans lequel les clés ont été vues. En parallèle, cet ordre change selon les blocs, et deux ex aequo pourraient s'échanger : le `diff` entre P1 et P2 échouerait sans qu'il y ait de bug.
- **24 heures garanties :** on parcourt `range(24)`, et le Counter renvoie 0 pour une heure absente.
- **Le temps d'analyse est sur la dernière ligne :** c'est la seule qui change d'une exécution à l'autre. Pour comparer P1 et P2, il suffit de l'enlever (`sed '$d'`).
- Les nombres sont affichés sans séparateur de milliers, pour se comparer facilement avec awk.

#### `src/analyse_seq.py`

- **Arguments :** on vérifie l'argument à la main avec `sys.argv`, pour avoir des messages en français (ceux d'`argparse` sont en anglais).
- **Codes de retour :**

  | Situation | Code |
  | --- | --- |
  | Tout va bien | 0 |
  | Fichier introuvable ou illisible | 1 |
  | Mauvaise utilisation (argument manquant) | 2 (convention Unix) |

- **Erreurs de fichier :** `FileNotFoundError` est attrapé avant `OSError`, car c'est un cas particulier. `OSError` couvre ensuite un dossier passé à la place d'un fichier ou un manque de droits.
- **Lecture :** `encoding="utf-8", errors="replace"`. Un octet invalide devient `�` au lieu de faire planter le programme.
- **Chronomètre :** `time.perf_counter()` démarre avant l'ouverture du fichier et s'arrête après l'analyse. La lecture du disque fait partie du coût réel, alors que la mise en forme (négligeable) n'est pas comptée. Le chronomètre de P2 compte en plus le découpage, la création des workers et la fusion, donc tout le surcoût du parallélisme (voir 6.3).

### 4.4 Décision : qu'est-ce qu'une ligne « mal formée » ?

- **Le constat :** le README du kit décrit le format mais ne définit pas une ligne mal formée. De plus, `generer_logs.py` ne produit que des lignes valides : l'échantillon contient 0 ligne défectueuse.
- **La question à l'encadrant :** on lui a proposé une règle.
- **Sa réponse :** *« ce qui nous intéresse, c'est que la date et l'heure soient cohérentes avec l'adresse IP et le code HTTP »*, avec la précision que l'intérêt de P1 est surtout de **mesurer le temps** sur 9 millions de lignes, pas de chercher des erreurs.

**Notre interprétation :** une ligne est valide si ses trois champs essentiels (IP, date/heure, code HTTP) sont exploitables.
Elle est ignorée dans l'un de ces cas :

| Contrôle | Pourquoi |
| --- | --- |
| Moins de 9 champs | Ligne vide ou tronquée |
| IP sans exactement 3 points, ou avec autre chose que des chiffres | IP inexploitable |
| Champ 4 qui ne commence pas par `[`, ou heure qui n'a pas 2 chiffres ou dépasse 23 | Date/heure inexploitable (sinon une « 25h » apparaîtrait) |
| Code HTTP qui n'a pas exactement 3 chiffres | Code inexploitable. Ce contrôle détecte aussi les champs décalés, par exemple une requête vide `"-"` |

**Choix assumés :**

- Les contrôles sont volontairement simples, puisque la priorité est la performance. Par exemple, on ne vérifie pas que chaque nombre de l'IP est entre 0 et 255.
- Le contrôle des guillemets autour de la requête, présent dans la première version, a été retiré. Il ne portait sur aucun des trois champs cités, et le contrôle du code détecte déjà le décalage.

### 4.5 Vérifications réalisées (sur l'échantillon)

| Vérification | Résultat |
| --- | --- |
| Exécution sur `data/echantillon_access.log` | 100 000 analysées, 0 ignorée, environ 0,3 s |
| Somme des requêtes par code = lignes analysées | 100 000 = 100 000 ✅ |
| Analysées + ignorées = `wc -l` | 100 000 = 100 000 ✅ |
| Somme des heures, et 24 lignes exactement | 100 000, 24 lignes ✅ |
| Codes comparés à `awk '{print $9}' … \| sort \| uniq -c` | Identiques ✅ |
| Top IP comparé à `cut -d' ' -f1 … \| sort \| uniq -c \| sort -rn \| head` | Identiques ✅ |
| Top pages comparé à `cut -d' ' -f7 …` | Identiques ✅ |
| Heures comparées à `cut -d' ' -f4 … \| cut -d: -f2 …` | Identiques ✅ |
| Lancement sans argument | Message sur stderr, code 2 ✅ |
| Fichier inexistant | « fichier introuvable », code 1 ✅ |
| Dossier à la place d'un fichier | « impossible de lire », code 1 ✅ |
| Fichier vide | Rapport à 0 avec les 24 heures, code 0 ✅ |
| Fichier de test de 10 lignes (voir ci-dessous) | 4 analysées, 6 ignorées ✅ |
| Fusion de 2 morceaux = analyse complète | Identique ✅ |

Les 6 lignes ignorées du fichier de test :

- une ligne vide ;
- une ligne tronquée ;
- une requête `"-"` ;
- une heure 25 ;
- un code `abc` ;
- une IP `serveur.local`.

Une ligne avec un octet invalide est, elle, bien analysée : l'octet est remplacé par `�`.

### 4.6 Comment lancer

```bash
# Sur l'échantillon (rapide)
python3 src/analyse_seq.py data/echantillon_access.log

# Générer le fichier complet (une seule fois, environ 2 min, 1,9 Go)
python3 scripts/generer_logs.py -o data/access.log

# Mesurer le temps de référence (à répéter 3 fois)
time python3 src/analyse_seq.py data/access.log > resultats/rapport_seq.txt
```

### 4.7 Limites connues (à savoir expliquer)

- **Espaces multiples :** `split()` les traite comme un seul séparateur, comme awk mais pas comme `cut -d' '`. Ça ne change rien sur ce journal.
- **Contrôle de l'IP :** il vérifie seulement la forme (4 nombres séparés par des points), pas les valeurs.
- **Tri des ex aequo :** il est alphabétique, pas numérique (`10.x` passe avant `9.x`). C'est déterministe, et c'est ce qui compte.
- **Dernière ligne sans `\n` :** elle serait comptée par Python mais pas par `wc -l`. Ça n'arrive pas avec le générateur.

---

## 5. Mesures de performance

À remplir après chaque mesure. Faire 3 exécutions et noter la médiane.

| Version | Fichier | Machine (cœurs) | Essai 1 | Essai 2 | Essai 3 | Médiane |
| --- | --- | --- | --- | --- | --- | --- |
| P1 séquentielle | échantillon (100 000 lignes) | — | ~0,3 s | | | |
| P1 séquentielle | access.log (9 M lignes) | VM Ubuntu OrbStack, i5-8210Y, 3 cœurs | 53,540 s | 61,662 s | 59,849 s | **59,849 s** |
### 5.1 Mesures P6 officielles (P1 + P2, même machine, même session)

Commande : `bash scripts/mesurer.sh data/access.log` → `resultats/mesures_p2_access.txt` et `.csv` (26/10/2026 14:49).

**Machine :** MacBook Air, macOS (directement, pas la VM), Intel Core i5-8210Y @ 1,60 GHz, **2 cœurs physiques / 4 threads** (hyperthreading), 8 Go de RAM, Python 3.15.0.
`os.cpu_count()` et `sysctl hw.ncpu` annoncent « 4 cœurs », mais `sysctl hw.physicalcpu` donne **2** : c'est la clé pour interpréter les résultats.
Depuis le 26/10, `mesurer.sh` écrit lui-même « 2 cœurs physiques, 4 cœurs logiques » (la ligne Machine du `.txt` a été corrigée à la main, sans relancer les mesures).

**Graphique :** `python3 scripts/tracer_graphique.py` → `resultats/graphique_p2_access.svg` (voir [6.3, étape 6](#étape-6--scriptstracer_graphiquepy--le-graphique-p6)).

| Version | Essai 1 | Essai 2 | Essai 3 | Médiane | Accélération |
| --- | --- | --- | --- | --- | --- |
| Séquentiel (P1) | 40,957 s | 34,321 s | 34,534 s | **34,534 s** | x1,00 |
| P2, 1 worker | 38,239 s | 35,506 s | 39,729 s | 38,239 s | x0,90 |
| P2, 2 workers | 27,369 s | 23,592 s | 23,962 s | **23,962 s** | **x1,44** |
| P2, 4 workers | 30,583 s | 26,727 s | 27,949 s | 27,949 s | x1,24 |
| P2, 8 workers | 30,238 s | 30,136 s | 27,389 s | 30,136 s | x1,15 |

Accélération = médiane séquentielle ÷ médiane de la version.

**Comment lire ces résultats (base de P7) :**

> **Mise à jour du 27/10 (P7, voir [section 11](#11-p7--analyse-des-limites)) :** la décomposition mesurée montre que la partie non parallélisable du **code** (démarrage, fusion) ne fait que 0,4 à 2,2 % du temps. L'écart à x2 avec 2 workers vient surtout de la **baisse de fréquence** quand 2 cœurs travaillent (+21 % de CPU), et de la lecture du disque. Les points ci-dessous restent justes sur le principe, mais la fusion est négligeable (16 ms au plus).

- **1 worker plus lent que P1 (x0,90) :** même travail qu'en P1, avec en plus le coût de P2 : créer un processus, découper, renvoyer les Counter par copie (pickle). C'est le **surcoût pur du parallélisme**.
- **2 workers = le meilleur (x1,44) :** un worker par cœur physique. Le gain n'est pas x2 car il reste une partie non parallélisable (démarrage des processus, fusion des Counter dans le processus principal, lecture du disque partagée) — loi d'Amdahl.
- **4 workers moins bien que 2 (x1,24) :** les 2 workers en plus tournent sur les threads hyperthreading, qui partagent les unités de calcul du même cœur physique : presque pas de calcul en plus, mais plus de processus à créer et plus de Counter à fusionner.
- **8 workers encore moins bien (x1,15) :** 8 processus pour 4 threads matériels, le système les fait tourner à tour de rôle (changements de contexte), et la fusion porte sur 8 résultats.
- **Écarts entre essais :** le i5-8210Y est un processeur basse consommation (série « Y ») dans un MacBook Air sans ventilateur : il baisse sa fréquence quand il chauffe. Le 1er essai de P1 (40,9 s) est aussi plus lent que les deux suivants (cache disque froid). D'où l'intérêt de la médiane.

**Vérification P3 sur le fichier complet** (`bash scripts/tester_p2.sh data/access.log`, même Mac) : rapports **IDENTIQUES** à P1 pour N = 1, 2, 4 et 8.

**Remarque :** les mesures P1 du tableau en haut de la section 5 (59,8 s) ont été faites dans la VM Ubuntu (3 cœurs virtuels). Elles ne se comparent pas aux mesures P2 du Mac : pour l'accélération, on n'utilise que le tableau ci-dessus, où P1 et P2 sont mesurés sur la même machine, dans la même session.

### 5.2 Essai du script sur l'échantillon

Notes sur P2 (essai du script sur l'échantillon, Mac, non officiel) :

- Sur 100 000 lignes, P2 est **plus lent** que P1 : environ 0,3 s pour P1, contre 0,5 à 3 s pour P2. Créer les processus et leur envoyer les résultats coûte plus cher que l'analyse elle-même, qui est très courte.
- C'est pour ça que les mesures de P6 se font sur le fichier complet, et c'est un argument pour P7 (coût de création des processus).
- `mesurer.sh` entrelace les essais (essai 1 de chaque version, puis essai 2…), pour qu'un ralentissement passager de la machine ne pénalise pas une seule version.

Notes sur les mesures P1 :

- Le temps retenu est celui affiché par le programme (« Temps d'analyse »). Le `real` de `time` est environ 0,2 s plus long, car il compte aussi le démarrage de Python.
- Les 3 rapports sont identiques, hors ligne du temps (vérifié avec `diff`).
- Une toute première exécution avait donné 79,160 s. Elle n'est pas retenue : elle a été lancée juste après la génération du fichier, et son rapport a été remplacé par celui de l'essai 1 (53,540 s, `resultats/rapport_seq.txt`).
- Les écarts entre essais (de 53 à 62 s) viennent de la machine : charge du Mac hôte, cache disque. C'est pour ça qu'on prend la médiane.

---

## 6. P2 — Version parallèle

### 6.1 Ce qui était demandé

| # | Demande (sujet P2 / plan de la section 6) | Fait | Où |
| --- | --- | --- | --- |
| 1 | Découper le fichier en N blocs, recalés sur les sauts de ligne | ✅ | `analyse_par.py` → `calculer_blocs()` |
| 2 | Faire analyser chaque bloc par un worker (`multiprocessing.Pool`) | ✅ | `lire_lignes()`, `analyser_bloc()` |
| 3 | Fusionner les résultats et écrire le rapport | ✅ | `main()` → `fusionner()`, `formater_rapport()` |
| 4 | Vérifier que le rapport est identique à P1 (hors temps) avec `diff`, pour N = 1, 2, 4, 8 | ✅ échantillon + `access.log` | `scripts/tester_p2.sh` (couvre aussi P3) |
| 5 | Mesurer les temps et calculer l'accélération | ✅ 3 essais, meilleure accélération x1,44 (N = 2) — voir [5.1](#51-mesures-p6-officielles-p1--p2-même-machine-même-session) | `scripts/mesurer.sh` (P6) |
| 6 | Graphique des temps et de l'accélération, machine décrite (processeur, cœurs) | ✅ | `scripts/tracer_graphique.py` → `resultats/graphique_p2_access.svg` |
| — | N choisi en ligne de commande, N invalide → message clair (P9) | ✅ | `main()`, `lire_nombre_workers()` |

### 6.2 Le principe

```
                         ┌─► worker 1 : analyser_bloc(octets 0 → b1)    ─┐
analyse_par.py           ├─► worker 2 : analyser_bloc(octets b1 → b2)   ─┤
  calculer_blocs() ──────┤   ...                                         ├──► fusionner() ──► formater_rapport()
  (N blocs)              └─► worker N : analyser_bloc(octets bN-1 → fin) ─┘    (processus principal)
```

- Le processus principal ne lit **pas** le fichier : il calcule seulement des positions (des octets). Chaque worker ouvre le fichier, se place au début de son bloc avec `seek()` et lit sa partie.
- Un worker ne reçoit que 3 petits paramètres `(chemin, debut, fin)` et renvoie son dictionnaire de Counter. On ne fait jamais passer les lignes entre les processus, ce qui serait très coûteux.
- **Aucune donnée partagée** entre workers : chacun a ses propres Counter, dans sa propre mémoire. La fusion est faite par le seul processus principal, *après* que tous les workers ont terminé. C'est l'argument pour **P4** (pas de section critique, donc pas de verrou nécessaire) et pour **P5** (pas de ressource attendue par deux processus, donc pas d'interblocage possible). Rédaction complète : [section 7](#7-p4--p5--section-critique-et-interblocage).

### 6.3 Ce qui a été fait, étape par étape

#### Étape 1 — `calculer_blocs(chemin, n)` : découper sans perdre ni doubler de ligne

1. On coupe d'abord « à la louche » : la frontière i est à `taille × i / n` octets.
2. Cette position tombe en général au milieu d'une ligne. On fait `seek()` dessus, puis `readline()`, qui avance jusqu'au `\n` suivant. La ligne entamée reste donc **entière dans le bloc précédent**.
3. La position atteinte (`tell()`) devient la fin du bloc i et le début du bloc i+1. Les blocs sont **contigus** : ni trou (ligne perdue), ni chevauchement (ligne comptée deux fois).
4. `max(..., borne précédente)` évite de reculer si une ligne était plus longue qu'un bloc. Les blocs vides (fichier minuscule, N grand) sont retirés.

Vérifié sur l'échantillon pour N = 1, 2, 3, 4, 7 et 8 : blocs contigus, chaque bloc commence en début de ligne, somme des lignes = 100 000.

#### Étape 2 — `lire_lignes()` et `analyser_bloc()` : le travail d'un worker

- Le worker lit son bloc **en binaire, par morceaux de 16 Mo** (`TAILLE_LECTURE`). Avec 1 worker, le bloc fait 1,9 Go : le lire d'un coup saturerait la mémoire.
- Chaque morceau est prolongé jusqu'au `\n` suivant (`readline()`), pour ne jamais couper une ligne. Ça ne coupe pas non plus un caractère accentué : en UTF-8, l'octet `\n` n'apparaît jamais au milieu d'un caractère.
- Le morceau est décodé avec `errors="replace"` (comme en P1), puis découpé avec `split("\n")`. On n'utilise pas `splitlines()`, qui coupe aussi sur d'autres caractères et pourrait donner un résultat différent de P1.
- Les lignes sont passées à `analyser_lignes()`, **la même fonction qu'en P1**.

Vérifié avec un vrai `Pool` : la fusion des résultats des workers est égale au résultat de P1 pour N = 1, 2, 4, 8, et aussi avec des morceaux forcés à 1 000 octets (pour tester le recollage des lignes coupées).

#### Étape 3 — `main()` : arguments, fusion, rapport

- Utilisation : `python3 src/analyse_par.py JOURNAL [N]`. **N est optionnel** : par défaut, le nombre de cœurs (`os.cpu_count()` : 4 sur le Mac, 3 dans la VM). C'est cohérent avec `lancer.sh JOURNAL [N]` du sujet (A4).
- Le chronomètre englobe **tout** le travail parallèle : découpage, création des workers, analyse, fusion. C'est la comparaison honnête avec P1 (qui compte lecture + analyse).
- `if __name__ == "__main__":` est **obligatoire**. Sur macOS (mode « spawn ») et sous Linux depuis Python 3.14 (mode « forkserver »), chaque worker démarre un nouvel interpréteur qui **réimporte** `analyse_par.py`. Sans ce test, chaque worker relancerait toute l'analyse. *(Vécu pendant le développement : un test lancé depuis l'entrée standard est resté bloqué, car les workers ne pouvaient pas réimporter le script.)*
- Codes de retour identiques à P1 :

  | Situation | Message | Code |
  | --- | --- | --- |
  | Tout va bien | rapport sur la sortie standard | 0 |
  | Fichier absent | `fichier introuvable : …` | 1 |
  | Dossier, droits insuffisants | `impossible de lire … : Is a directory` | 1 |
  | Aucun argument / trop d'arguments | `il faut indiquer le journal` + utilisation | 2 |
  | N = `0`, `-3`, `abc` | `N doit être un entier supérieur ou égal à 1 (reçu : …)` | 2 |

#### Étape 4 — `scripts/tester_p2.sh` : la preuve par `diff` (P3)

- Lance P1 une fois, puis P2 avec N = 1, 2, 4 et 8, et compare : `diff <(sed '$d' seq.txt) <(sed '$d' par_N.txt)` (`sed '$d'` retire la dernière ligne, le temps).
- Code de retour 0 si tout est identique, 1 sinon (avec la différence affichée).
- Se place tout seul à la racine du dépôt (`dirname "$0"`) : aucun chemin absolu, il marche depuis n'importe quel dossier et sur le poste d'un autre membre.
- Fichiers temporaires dans `mktemp -d`, supprimés automatiquement (`trap ... EXIT`).

Résultat sur l'échantillon : **IDENTIQUE pour N = 1, 2, 4 et 8**.

Cas limites vérifiés aussi (P1 et P2 identiques pour N = 1, 2, 4, 8) :

- fichier vide ;
- fichier de 11 lignes avec une ligne vide, une ligne tronquée, une requête `"-"`, une heure 25, un code `abc`, une IP `serveur.local` (6 ignorées), un octet invalide et une dernière ligne sans `\n` (5 analysées).

#### Étape 5 — `scripts/mesurer.sh` : les mesures (P6)

- `bash scripts/mesurer.sh JOURNAL [ESSAIS]` (3 essais par défaut) : P1, puis P2 avec N = 1, 2, 4, 8.
- Relève le « Temps d'analyse » affiché par le programme (même mesure qu'en P1), calcule la **médiane** et l'**accélération** = médiane P1 ÷ médiane P2.
- Décrit la machine automatiquement : processeur, **cœurs physiques et logiques**, version de Python, date.
  - Linux : `lscpu -p=Core,Socket | sort -u | wc -l` (une ligne par cœur logique ; deux cœurs logiques avec le même couple cœur/socket sont sur le même cœur physique) et `nproc`.
  - macOS : `sysctl hw.physicalcpu` et `hw.logicalcpu`.
  - *Pourquoi :* avec l'hyperthreading, 2 cœurs logiques partagent les unités de calcul d'un cœur physique. Pour du calcul pur, c'est le nombre de cœurs physiques qui limite l'accélération.
  - Vérifié : Mac → « 2 physiques, 4 logiques » ; VM OrbStack → « 2 physiques, 3 logiques » (OrbStack ne donne que 3 processeurs à la VM : `nproc` = 3, `nproc --all` = 4).
- Écrit `resultats/mesures_p2_<journal>.txt` (tableau lisible) et `.csv` (données pour tracer le graphique demandé par P6).

#### Étape 6 — `scripts/tracer_graphique.py` : le graphique (P6)

- `python3 scripts/tracer_graphique.py [MESURES.csv]` (par défaut `resultats/mesures_p2_access.csv`) affiche les médianes et l'accélération, puis écrit `resultats/graphique_p2_access.svg` à côté du `.csv`.
- **Pourquoi un SVG écrit « à la main » :** matplotlib est interdit (bibliothèque standard uniquement). Un SVG est un simple fichier texte (`<rect>`, `<line>`, `<circle>`, `<text>`) : quelques petites fonctions qui écrivent ces balises suffisent. Le navigateur l'affiche, on peut l'insérer dans le PDF, et il reste net quand on zoome (dessin vectoriel). Le fichier fait 8 Ko.
- **Panneau de gauche :** un bâton par version = temps médian ; les 3 essais en points noirs (on voit la dispersion) ; la meilleure accélération en orange.
- **Panneau de droite :** accélération mesurée selon N, comparée à l'**accélération idéale = N** (pointillés) et au repère « séquentiel x1 ». Les N (1, 2, 4, 8) sont espacés régulièrement : chacun est le double du précédent (échelle logarithmique en base 2). L'écart entre les deux courbes est ce qu'explique P7.
- **Fonctions :**
  - `lire_mesures()` : lit le CSV avec `csv.DictReader` (colonnes lues par leur nom, pas par leur position) ;
  - `calculer_resume()` : `statistics.median`, même calcul que `mesurer.sh` ;
  - `panneau_temps()`, `panneau_acceleration()`, `dessiner_svg()` : le dessin.
- **Erreurs :**
  - fichier absent ou illisible → code 1 ;
  - ligne mal formée (temps non numérique ou nul, version ni `seq` ni entier), ou pas de mesure `seq` → message avec le numéro de ligne, code 1 ;
  - plus d'un argument → code 2.
  Un temps nul est refusé parce qu'on divise par lui.

Vérifications :

| Vérification | Résultat |
| --- | --- |
| Médianes et accélérations affichées = `mesures_p2_access.txt` | Identiques ✅ |
| SVG = XML valide (`xml.dom.minidom`) | ✅ |
| Relancé depuis `/` : même fichier (`cmp`) | Identique, déterministe ✅ |
| CSV construit à partir de vrais passages sur l'échantillon | Graphique correct (les temps sont du bruit, 0,9 à 3 s : confirme qu'on mesure sur le fichier complet) ✅ |
| CSV ne contenant que `seq` | Plantait (`max()` sur une liste vide) → corrigé avec `default=None` ✅ |
| Fichier absent, dossier, 2 arguments, lignes mal formées, fichier vide | Codes 1 / 1 / 2 / 1 / 1, messages clairs ✅ |
| Aperçu visuel (converti en image avec `qlmanage`) | Lisible, chevauchements d'étiquettes corrigés (liseré blanc `paint-order="stroke"`) ✅ |

### 6.4 Comment lancer

```bash
# Rapport parallèle avec 4 workers
python3 src/analyse_par.py data/echantillon_access.log 4

# Vérifier P1 = P2 (échantillon : quelques secondes ; fichier complet : ~5 min)
bash scripts/tester_p2.sh
bash scripts/tester_p2.sh data/access.log

# Mesures officielles (~15 min, ne pas utiliser la machine pendant ce temps)
# Faites le 26/10 sur le Mac directement (pas la VM), voir 5.1
bash scripts/mesurer.sh data/access.log

# Graphique P6 à partir du .csv (instantané)
python3 scripts/tracer_graphique.py
```

### 6.5 Limites connues (à savoir expliquer)

- **Petit fichier :** P2 est plus lent que P1 sur l'échantillon. Le coût fixe (créer N interpréteurs Python, les importer, renvoyer les Counter) dépasse le gain.
- **Fusion séquentielle :** `fusionner()` tourne dans le seul processus principal. Avec beaucoup d'IP et de pages différentes, c'est une partie non parallélisable (loi d'Amdahl, P7). Mesurée le 27/10 sur `access.log` : 16 ms au plus (section 11).
- **Résultats envoyés par copie :** chaque worker renvoie ses Counter « picklés » (sérialisés) au processus principal. Plus il y a de workers, plus il y a de données à envoyer et à fusionner.
- **Plus de workers que de cœurs :** avec N = 8 sur 3 ou 4 cœurs, les workers se partagent les cœurs à tour de rôle : pas de gain, voire une perte.
- **Retour chariot `\r` :** P1 (mode texte) le traite comme une fin de ligne, P2 (`split("\n")`) non. Le générateur n'en produit jamais (vérifié : 0 dans l'échantillon), donc les rapports restent identiques.

---

## 7. P4 / P5 — Section critique et interblocage

### 7.1 Ce qui était demandé

| # | Demande (sujet) | Fait | Où |
| --- | --- | --- | --- |
| P4 | Identifier chaque donnée partagée entre workers et la protéger par un verrou ; **si aucune, le démontrer** | ✅ démontré : aucune donnée partagée en écriture | `docs/concurrence_P4_P5.md` §1, `scripts/demontrer_p4.py` |
| P5 | Expliquer avec les conditions de Coffman pourquoi le programme ne peut pas se bloquer, avec le graphe ressources / processus | ✅ | `docs/concurrence_P4_P5.md` §2 |

**Pourquoi un fichier à part :** ce document-ci n'est pas versionné. La rédaction P4 / P5 fait partie du rapport de performance, elle doit donc être dans le dépôt : `docs/concurrence_P4_P5.md`, qui servira de source pour le PDF.

### 7.2 P4 — Ce qu'il faut savoir expliquer

- **Pas de mémoire partagée :** les workers sont des **processus**, chacun a son propre espace mémoire (`spawn` / `forkserver` : nouvel interpréteur ; `fork` : copie). Pour partager, il faudrait `Value`, `Array`, `Manager` ou `shared_memory` : `grep` sur `src/` → aucun.
- **Inventaire (10 données)** dans `concurrence_P4_P5.md` §1.3 : paramètres envoyés par copie, Counter propres à chaque worker, résultat renvoyé par `return`, fusion par le seul principal **après** `starmap`, pas de compteur d'avancement, rapport et stdout écrits par le seul principal, journal lu en lecture seule, blocs disjoints, constantes.
- **Point subtil :** chaque worker fait **son propre `open()`**, donc il a sa propre position de lecture. Un descripteur partagé ferait qu'un `seek()` d'un worker déplace la lecture des autres.
- **Choix de conception :** partitionner + calculer localement + fusionner une fois. Plus rapide aussi : un verrou sur des Counter communs serait pris 9 millions de fois.
- **Verrous internes du `Pool` :** il y en a (files des tâches et des résultats), mais c'est la bibliothèque qui les gère, pas notre code.

### 7.3 P4 — La preuve à l'exécution : `scripts/demontrer_p4.py`

- `python3 scripts/demontrer_p4.py [JOURNAL] [N]` (par défaut : échantillon, 4 workers).
- Appelle la **vraie** `analyser_bloc()` de P2 (sans la modifier). Chaque tâche ajoute aussi ses lignes à une variable globale `LIGNES_VUES` et renvoie son PID.
- 4 vérifications : PID des workers ≠ PID du principal ; `LIGNES_VUES` = **0** dans le principal ; somme des blocs = total ; fusion = séquentiel.
- Codes : 0 = démonstration vérifiée, 1 = échec ou fichier absent / illisible, 2 = mauvaise utilisation.
- Le chemin vers `src/` est calculé depuis l'emplacement du script : il marche depuis n'importe quel dossier.

| Vérification | Résultat |
| --- | --- |
| Échantillon, N = 4 | 4 PID distincts, `LIGNES_VUES` = 0, 100 000 lignes, fusion = séquentiel, code 0 ✅ |
| Échantillon, N = 8 | 8 PID distincts, mêmes résultats, code 0 ✅ |
| Lancé depuis `/` | OK ✅ |
| Fichier absent / dossier / N = 0 / 3 arguments | Codes 1 / 1 / 2 / 2, messages clairs ✅ |
| **Contre-épreuve** : même script avec des threads (`multiprocessing.dummy.Pool`, copie temporaire) | 1 seul PID, `LIGNES_VUES` = 100 000, code 1 : le test **sait** détecter un partage ✅ |

La contre-épreuve montre aussi qu'avec des threads, `LIGNES_VUES += lignes` deviendrait une vraie section critique (lien avec P8).

### 7.4 P5 — Ce qu'il faut savoir expliquer

- **Coffman :** un interblocage exige les 4 conditions **en même temps** ; il suffit d'en casser une.
- **Graphe ressources / processus** (Holt : cercle = processus, carré = ressource) : le seul chemin d'attente est « principal → file des résultats → worker », et le worker n'attend rien. Graphe d'attente = arbre, **aucun cycle**.

| Condition | Chez nous |
| --- | --- |
| 1. Exclusion mutuelle | Presque absente (journal en lecture partagée, mémoire séparée) ; seuls les verrous internes du `Pool`, un instant |
| 2. Détention et attente | **Absente** : un worker ne garde jamais une ressource en en attendant une autre ; le principal ne détient rien (son fichier de `calculer_blocs()` est fermé avant le `Pool`) |
| 3. Pas de réquisition | Partielle (les cœurs sont réquisitionnés par le noyau) |
| 4. Attente circulaire | **Absente** : aucun cycle |

- **Question piège :** un worker qui a fini attend une nouvelle tâche (flèche worker → principal). Pas de cycle : il a déjà rendu son résultat, et le `Pool` envoie les tâches et lit les résultats avec deux threads internes différents (vérifié dans `multiprocessing/pool.py`, lignes 238 et 247 en Python 3.15).
- **Limites (attente sans fin, mais pas un interblocage) :**
  - oubli de `if __name__ == "__main__":` (vécu, voir 6.3 étape 3) ;
  - **worker tué** (manque de mémoire, `kill -9`) : la tâche est perdue et `starmap` attend sans fin. **Vérifié** sur le Mac (Python 3.15) avec un petit test séparé : `map_async(...).get(timeout=10)` toujours en attente après 10 s. Risque limité par la lecture par morceaux de 16 Mo. Amélioration possible, non faite : `ProcessPoolExecutor` (lève `BrokenProcessPool`) ou un `timeout`.

---

## 8. Scripts Bash A2 à A8

### 8.1 Ce qui était demandé

| # | Demande (sujet) | Fait | Où |
| --- | --- | --- | --- |
| A2 | Une seule commande crée l'arborescence, vérifie les prérequis, pose les droits ; la relancer ne casse rien | ✅ | `scripts/installer.sh` |
| A3 | Groupe de l'équipe ; un extérieur ne lit pas `data/` et ne lance pas les scripts ; `archives/` au propriétaire seul ; aucun 777 ; tableau des droits en octal justifié | ✅ prouvé avec 2 utilisateurs de test | `installer.sh`, `docs/droits_A3.md` |
| A4 | `bash scripts/lancer.sh JOURNAL [N]` : N workers, rapport horodaté dans `resultats/` ; erreurs : message clair, code ≠ 0 | ✅ | `scripts/lancer.sh` |
| A5 | Script de commandes du cours reliées par des tubes, recalcule au moins les indicateurs 1 et 2, enregistrés par redirection, mêmes nombres que Python | ✅ indicateurs 1 et 2 | `scripts/controle.sh` |
| A7 | Supprime temporaires et rapports de plus de N jours, après confirmation ou avec une option ; jamais `data/` ni `archives/` | ✅ | `scripts/nettoyer.sh` |
| A8 | Archive `.tar.gz` horodatée de `resultats/` dans `archives/`, lisible du seul propriétaire | ✅ | `scripts/archiver.sh` |

Tous les scripts suivent le même modèle que `tester_p2.sh` : ils se placent à la racine avec `dirname "$0"` (aucun chemin absolu), écrivent les erreurs sur stderr, et renvoient **0 = OK, 1 = fichier absent ou illisible, 2 = mauvaise utilisation**.

### 8.2 Ce qu'il faut savoir expliquer, script par script

#### `lancer.sh JOURNAL [N]` (A4)

- Rapport écrit dans `resultats/rapport_AAAAMMJJ_HHMMSS_NOM_NN.txt` (ex. `rapport_20261027_103353_echantillon_access_N4.txt`).
- **N par défaut :** calculé par le script (`getconf _NPROCESSORS_ONLN`, marche sous Linux et macOS) puis passé à Python. Le nom du fichier indique donc toujours le vrai N.
- **Mêmes contrôles que Python, mais avant le lancement :** argument manquant ou en trop (code 2), N pas un entier ≥ 1 (code 2), fichier absent ou dossier (code 1).
- **Si Python échoue, le rapport est supprimé :** jamais de rapport vide ou incomplet dans `resultats/`.
- `umask 027` : le rapport est créé directement en 640 (tableau A3).
- Rapports non versionnés (`.gitignore` : `resultats/rapport_[0-9]*.txt`), sinon chaque lancement ajouterait un fichier au dépôt. Le motif commence par un chiffre : `rapport_seq.txt` reste versionné.

#### `controle.sh JOURNAL` (A5)

- `cut -d' ' -f9 | sort -n | uniq -c` pour les codes ; `cut -d' ' -f1 | sort | uniq -c | sort -k1,1nr -k2,2 | head -n 10` pour le top 10 IP. Résultat dans `resultats/controle_NOM.txt`.
- **`uniq -c` ne compte que des lignes identiques qui se suivent :** il faut trier avant.
- **`sort -k1,1nr -k2,2` :** nombre décroissant, puis IP croissante, la même règle que `top()` dans `rapport.py`.
- **`LC_ALL=C` :** tri octet par octet, comme Python (même ordre des ex aequo), et plus rapide.
- **Les accolades `{ ... } > fichier`** regroupent toutes les sorties dans une seule redirection.
- **Limite à connaître :** le shell ne filtre pas les lignes mal formées. Les nombres sont égaux à ceux de Python parce que le journal en contient 0.

#### `archiver.sh` (A8)

- `tar -czf archives/resultats_AAAAMMJJ_HHMMSS.tar.gz resultats` : `c` créer, `z` gzip, `f` nom de l'archive. Chemin relatif : l'archive ne contient pas le chemin de la machine.
- **`umask 077` avant `tar` :** l'archive naît en 600. Un `chmod` après coup laisserait un court instant où elle est lisible par d'autres. Le `chmod 600` reste en plus, par sécurité.
- Refuse d'écraser une archive existante (deux lancements dans la même seconde).
- Archives non versionnées (`.gitignore` : `archives/*.tar.gz`) : les mettre sur Git les rendrait lisibles par toute personne ayant accès au dépôt, ce qui contredit A3.

#### `nettoyer.sh [-o] [N]` (A7)

- Supprime les dossiers `__pycache__`, les fichiers `*.pyc`, `*.tmp`, `*~`, et les rapports de `lancer.sh` de plus de N jours (7 par défaut, `0` = tous).
- **`data/` et `archives/` sont protégés par construction :** `find` ne reçoit que `src scripts resultats docs` comme points de départ, il ne visite jamais les deux autres.
- Les résultats officiels (`rapport_seq.txt`, mesures, graphique, contrôle) ne correspondent pas au motif `rapport_[0-9]*.txt` : jamais supprimés.
- **`-mmin +N×1440` plutôt que `-mtime +N` :** `-mtime` arrondit à la journée entière (`-mtime +7` veut dire au moins 8 jours) ; `-mmin` donne « plus de N × 24 h » exactement.
- Affiche la liste, puis demande `[o/N]` (non par défaut) ; `-o` supprime sans demander.

#### `installer.sh [GROUPE]` (A2 + A3)

1. Vérifie les prérequis (Python ≥ 3.8, multiprocessing, `grep cut sort uniq wc head tail find chmod chgrp tar gzip date`) ; s'il en manque un, code 1 sans rien modifier.
2. Crée les dossiers manquants (`mkdir -p`).
3. Si on est membre du groupe (`paralog` par défaut) : `chgrp` du projet (pas de `.git/`). Sinon : avertissement + les commandes `sudo groupadd` / `usermod -aG` à faire lancer une fois par un administrateur. **Le script n'appelle pas `sudo` lui-même** (choix validé).
4. Pose les droits du tableau A3.

- **Pourquoi le relancer ne casse rien :** `mkdir -p` ne fait rien si le dossier existe, et les droits sont posés en valeur absolue (`chmod 750`) et non relative (`chmod +x`). Vérifié : droits identiques avant et après une relance (`diff` de `find -printf`).
- **Effet sur git :** git enregistre le bit `x`. `tester_p2.sh`, `mesurer.sh` et `verifier_environnement.sh` sont passés de 644 à 755 (« mode change ») : changement à commiter, aucun contenu modifié.

### 8.3 Les droits (A3)

Tableau complet et justifications : `docs/droits_A3.md`. En résumé :

| Élément | Octal |
| --- | --- |
| racine, `data/`, `src/`, `scripts/`, `docs/` | 750 |
| `resultats/` | **2770** (écriture du groupe + setgid) |
| `archives/` | **700** |
| `scripts/*.sh` | 750 |
| autres fichiers (`.py`, `.log`, docs, rapports) | 640 |
| `archives/*.tar.gz` | 600 |

- **setgid sur `resultats/` :** un fichier créé dedans prend le groupe du dossier (`paralog`), et non le groupe personnel de son auteur. Sans lui, un rapport de coequipier serait en `coequipier:coequipier`, illisible par l'équipe.
- **`.py` en 640 :** on lance `python3 fichier.py`, c'est l'interpréteur qui est exécuté, le fichier est seulement lu.
- **Code 126 :** code de retour de Bash quand l'exécution est refusée (permission).

### 8.4 Vérifications réalisées (27/10, VM Ubuntu 26.04 + Mac)

| Vérification | Résultat |
| --- | --- |
| `lancer.sh` échantillon N = 4, sans N, depuis `/tmp` | Rapports écrits, code 0 ; rapport = P1 hors temps (`diff`) ✅ |
| `lancer.sh` sans argument / 3 arguments / fichier absent / dossier / N = `0`, `abc`, `-3` | Codes 2 / 2 / 1 / 1 / 2 ✅ |
| `controle.sh` échantillon | Codes HTTP et top 10 IP identiques à Python (nombres et ordre) ✅ |
| `controle.sh` sur un fichier avec ex aequo | Même ordre que Python (`10.x` < `172.x` < `192.x` < `9.x`) ✅ |
| `archiver.sh` | Archive 600, `archives/` 700, contenu extrait = `resultats/` (`diff -r`) ✅ |
| `nettoyer.sh` avec des pièges (`.tmp`, vieux `rapport_…`) dans `data/` et `archives/` | Pièges intacts, `rapport_seq.txt` intact, rapport de 10 jours supprimé, rapports du jour gardés ✅ |
| `nettoyer.sh` réponse `n` / `o` / `-o 0` / arguments invalides | Rien supprimé / supprimé / tous les rapports / code 2 ✅ |
| `nettoyer.sh 0` juste après un lancement | Corrigé : `-mmin +0` oubliait les rapports de moins d'une minute → cas `N = 0` traité à part ✅ |
| `installer.sh` sur une copie « poste vierge » (`/tmp/paralog_test`), sans groupe | Dossiers créés, avertissement + commandes sudo, code 0 ✅ |
| `installer.sh` relancé | Droits identiques ✅ |
| Preuve A3 avec `coequipier` (groupe) et `exterieur` | Voir `docs/droits_A3.md` §3 : l'équipe lit et lance, l'extérieur rien, `archives/` au propriétaire seul ✅ |
| Aucun 777 / aucun fichier inscriptible par les autres | 0 ✅ |
| `installer.sh` sur le vrai dépôt, puis `tester_p2.sh` | Groupe `paralog` appliqué, P3 toujours IDENTIQUE ✅ |

**Mis en place dans la VM :** groupe `paralog` (louis membre), utilisateurs de test `coequipier` (dans le groupe) et `exterieur`, **gardés pour la démo de mercredi**. À supprimer après la soutenance : `sudo userdel -r coequipier && sudo userdel -r exterieur`.

**Remarque :** dans `/home/louis/paralog`, coequipier ne peut pas entrer car `/home/louis` est en 750. La preuve se fait donc sur une installation dans un dossier commun (`/tmp/paralog_test`, comme `/srv/paralog` sur un vrai serveur).

### 8.5 Comment lancer

```bash
bash scripts/installer.sh                              # A2 + A3 (relançable)
bash scripts/lancer.sh data/echantillon_access.log 4   # A4
bash scripts/controle.sh data/echantillon_access.log   # A5
bash scripts/nettoyer.sh 7                             # A7 (avec confirmation ; -o sans)
bash scripts/archiver.sh                               # A8

# Fichier complet (à lancer par Louis) :
time bash scripts/controle.sh data/access.log          # ~1 min, comparer à resultats/rapport_seq.txt
```

---

## 9. A6 — Schéma en couches et appels système

### 9.1 Ce qui était demandé

| # | Demande (sujet) | Fait | Où |
| --- | --- | --- | --- |
| A6 | Un schéma situe l'utilisateur, les scripts, le programme, l'interpréteur Python, le noyau et le matériel | ✅ 7 couches (+ bibliothèque C, + frontière des appels système) | `docs/schema_A6.md` §1, `docs/schema_A6.svg` |
| A6 | Il montre au moins deux appels système utilisés (lecture de fichier, création de processus) | ✅ 8 appels **relevés réellement** : `clone`, `vfork`, `execve`, `openat`, `lseek`, `read`, `dup2`, `write` | `docs/schema_A6.md` §2–3, `scripts/tracer_appels.sh` |

**Pourquoi des appels relevés et pas seulement cités :** une fonctionnalité doit être démontrable devant le tuteur. `bash scripts/tracer_appels.sh` refait le relevé en quelques secondes.

### 9.2 `scripts/tracer_appels.sh [JOURNAL] [N]`

- Par défaut : échantillon, N = 2. Lance `strace -f -ff -s 80 -o TMP/trace bash scripts/lancer.sh JOURNAL N`.
  - `-f` : suit les processus fils (python3, forkserver, workers) ;
  - `-ff` : un fichier par processus (`trace.PID`), donc les lignes de deux processus ne se coupent jamais ;
  - `-s 80` : chaînes tronquées à 80 caractères (à 40, le mot `forkserver` disparaissait).
- Un `awk` par fichier garde les appels utiles et donne un rôle au processus d'après le **programme** de son `execve` (pas ses arguments : `dirname scripts/lancer.sh` était pris pour bash). Un processus sans `execve` qui ouvre le journal est un worker.
- Les `read` du journal sont **comptés** (nombre, octets), pas affichés un par un ; les threads (`CLONE_THREAD`) aussi. Le `dup2` n'est gardé que s'il suit l'ouverture du rapport (sinon bruit interne de bash).
- Trace brute dans `mktemp -d`, supprimée par `trap`. Codes : 0 = OK ; 1 = `strace` absent (Mac) ou lancement en échec ; 2 = trop d'arguments. Fichier absent ou N invalide : c'est `lancer.sh` qui répond, son code est renvoyé.
- **Linux seulement** : `strace` n'existe pas sous macOS (`dtruss` demande de désactiver SIP). Installé dans la VM le 27/10 (`sudo apt install strace`, version 6.19).

### 9.3 Ce qu'il faut savoir expliquer

- **Mode utilisateur / mode noyau :** un programme ne touche jamais le matériel directement ; il demande au noyau par un appel système, qui vérifie (droits, paramètres), exécute, rend la main. La glibc traduit `open()`, `read()`, `fork()` en appels système.
- **`clone` puis `execve` :** créer un processus (copie du parent, nouveau PID) et lancer un programme (remplace le programme, **même PID**) sont deux étapes. bash fait les deux pour lancer python3. Les workers ne font que `clone` : copies du forkserver, qui contient déjà Python et notre code.
- **Le PID de python3 fait `openat(rapport)` + `dup2(3, 1)` avant son `execve` :** c'est encore le fils de bash qui prépare la redirection `>`.
- **Processus ou thread = même appel :** `clone` sans `CLONE_VM` → processus, mémoire séparée (workers) ; `clone3` avec `CLONE_VM|CLONE_THREAD` → thread, mémoire partagée (3 threads internes du Pool). Preuve P4 côté noyau, et lien avec P8.
- **`vfork` :** utilisé par Python pour démarrer le forkserver et le resource_tracker, suivi aussitôt d'un `execve` ; le parent attend l'`execve`, c'est plus rapide qu'une copie complète.
- **Le découpage se voit :** le principal fait `lseek(3, 10297143)` (milieu) puis lit 128 Kio pour finir la ligne ; le worker 2 commence à 10 297 292 et lit exactement 20 594 286 − 10 297 292 = 10 296 994 octets.
- **Le worker 1 lit 57 396 octets de trop :** Python lit par multiples de son tampon de 128 Kio (1er `read` = 78 × 131 072 = 10 223 616), puis un tampon complet pour la fin du bloc. Le surplus reste dans le tampon, `fichier.read()` ne rend que le bloc : jamais analysé. *(Première explication donnée en séance — « le tampon de `readline()` » — fausse, corrigée.)*
- **Peu de `read` :** 2 par worker sur l'échantillon, grâce aux morceaux de 16 Mo. Chaque appel système coûte un passage en mode noyau.
- **Droits A3 vérifiés par le noyau à `openat` :** vérifié dans la VM sur un fichier 640 dans un dossier 750 (groupe `paralog`) : `exterieur` → `-1 EACCES`, `coequipier` → descripteur 3. Python en fait une `PermissionError`, attrapée par nos programmes (« impossible de lire », code 1).
- **Python 3.14 sous Linux :** méthode `forkserver` par défaut (avant 3.14 : `fork`, le principal ferait lui-même `clone`). L'appel système est le même.

### 9.4 Vérifications réalisées (27/10, VM Ubuntu, échantillon)

| Vérification | Résultat |
| --- | --- |
| `tracer_appels.sh` sans argument (N = 2) | Résumé correct : bash → python3 → forkserver → 2 workers, 3 threads, code 0 ✅ |
| N = 4, lancé depuis `/` | 4 workers créés par `clone` depuis le forkserver, code 0 ✅ |
| Rapports produits sous strace (N = 2 et 4) | Identiques à P1 hors temps (`diff`) ✅ |
| Mac (pas de strace) / 3 arguments / fichier absent / N = 0 | Codes 1 / 2 / 1 / 2, messages clairs ✅ |
| Octets lus par le worker 2 = taille − début de bloc | 10 296 994 = 10 296 994 ✅ |
| `exterieur` / `coequipier` sur un fichier 640 (dossier 750) | `EACCES` / descripteur 3 ✅ |
| `schema_A6.svg` | XML valide ; aperçu Chrome headless lisible, sans chevauchement ✅ |

### 9.5 Comment lancer

```bash
# Dans la VM Ubuntu (Linux), depuis la racine du dépôt
bash scripts/tracer_appels.sh                              # échantillon, 2 workers
bash scripts/tracer_appels.sh data/echantillon_access.log 4
# Schéma : ouvrir docs/schema_A6.svg dans un navigateur
```

Les temps affichés sous `strace` ne sont pas des mesures (chaque appel est intercepté). Chaque lancement laisse un rapport `resultats/rapport_…` (non versionné, supprimé par `nettoyer.sh`).

---

## 10. Dossier d'architecture (PDF)

### 10.1 Ce qui était demandé

| Livrable (sujet) | Fait | Où |
| --- | --- | --- |
| Dossier d'architecture : schéma en couches, arborescence commentée, tableau des droits, mode d'emploi des scripts (A1 à A9), **PDF, 10 pages max** | ✅ 10 pages (9 jusqu'à l'ajout de `mesurer_limites.py` le 27/10 : les pages 7 à 10 sont décalées d'une demi-page par rapport au tableau 10.2) | `docs/dossier_architecture.pdf` |

### 10.2 Contenu, page par page

| Page | Contenu |
| --- | --- |
| 1 | Page de garde (champs **surlignés en jaune** à compléter : équipe, chef de projet, noms) |
| 2 | Tableau de couverture A1–A9 (section, commande de démo, état ; A9 « non réalisé ») + 1. Présentation (besoin, principe P1/P2, environnement, codes de retour) |
| 3–4 | 2. Arborescence commentée (A1) : arbre complet + tableau « rôle / qui y écrit / sur Git ? » + pourquoi cette séparation |
| 4–5 | 3. Schéma en couches (A6) : `schema_A6.svg`, mode utilisateur / noyau, 8 appels système, trace résumée, 5 points clés |
| 5–6 | 4. Droits (A3) : groupe, tableau octal justifié, aucun 777, preuve coequipier / exterieur, EACCES |
| 7–9 | 5. Mode d'emploi : récapitulatif des 12 scripts, fiches A2, A4, A5, A7, A8 avec sorties réelles, scénario de démo |
| 9 | 6. Limites, A9 non réalisé, encadré « Usage d'un outil d'IA » (obligatoire d'après les règles du sujet) |

### 10.3 Choix techniques (à savoir expliquer)

- **Source HTML + Chrome headless (`--print-to-pdf`)** : pas de pandoc ni de bibliothèque Python de PDF (bibliothèque standard uniquement). Le SVG du schéma est inclus tel quel, donc **vectoriel** (net au zoom). La source est un fichier texte versionné : un coéquipier peut la corriger et régénérer.
- **CSS d'impression** : `@page` (A4, marges, numéro de page « n / total » en pied de page), `break-before: page` pour la page de garde et les grandes parties, `break-after: avoid` sur les titres (jamais de titre seul en bas de page), `white-space: nowrap` sur la notation `rwxr-x---`.
- **`scripts/generer_pdf.sh`** : cherche le navigateur dans l'ordre variable `CHROME` → `google-chrome`, `chromium`… dans le PATH → application macOS. `umask 027` (PDF en 640). Compte les pages avec `grep -ao '/Type */Pages*' | grep -cv 'Pages$'` : un objet `/Type /Page` par page, on retire `/Type /Pages` (la liste des pages). *(Première version avec `[^s]` : 0 page, car `/Page` est suivi d'un saut de ligne et grep lit ligne par ligne — corrigé.)*
- **Sorties réelles** : tous les scripts ont été relancés le 27/10 sur l'échantillon, dans une **copie du dépôt** (scratchpad), pour ne rien ajouter au vrai dépôt. La sortie d'`installer.sh` est abrégée et correspond à la VM (groupe `paralog` présent).

### 10.4 Vérifications réalisées (27/10, Mac)

| Vérification | Résultat |
| --- | --- |
| `generer_pdf.sh` depuis la racine et depuis `/` | PDF écrit, 9 pages, code 0 ✅ |
| Argument en trop / `CHROME=/nexiste/pas` | Codes 2 / 1, messages clairs ✅ |
| Nombre de pages du script = PDFKit (macOS) | 9 = 9 ✅ |
| Relecture des 9 pages en image (PDFKit via `osascript -l JavaScript`) | Pas de texte coupé, pas de titre orphelin ✅ |
| Scripts relancés dans la copie : `lancer.sh` (4 / sans arg / absent / N=0), `controle.sh`, `tester_p2.sh`, `demontrer_p4.py`, `archiver.sh`, `nettoyer.sh` (n / -o 0 / abc), `tracer_appels.sh` (Mac) | Codes 0/2/1/2, nombres = Python, IDENTIQUE, 4 OK, archive 600, rien / 2 supprimés / code 2, code 1 ✅ |

**Découvert pendant les tests :** dans la copie (`/private/tmp`, groupe `wheel` hérité du dossier parent), `installer.sh` s'arrête sur `chmod 2770 resultats` (« Operation not permitted », code 1) : on ne peut pas poser le setgid sur un dossier dont on n'est pas membre du groupe. Après `chgrp -R staff`, code 0 et relance code 0. Pas un bug pour une installation normale ; noté dans les limites du dossier, script non modifié.

### 10.5 Comment lancer

```bash
bash scripts/generer_pdf.sh        # -> docs/dossier_architecture.pdf (sans argument = dossier d'architecture)
# Après modification du .html (ex. noms de la page de garde), relancer la même commande.
```

---

## 11. P7 — Analyse des limites

### 11.1 Ce qui était demandé

| # | Demande (sujet) | Fait | Où |
| --- | --- | --- | --- |
| P7 | Expliquer pourquoi le gain n'est pas proportionnel au nombre de workers : nombre de cœurs, coût de création des processus, lecture du disque, partie non parallélisable | ✅ chaque cause **mesurée**, pas seulement supposée | `docs/limites_P7.md`, `scripts/mesurer_limites.py`, `resultats/limites_access.txt` |

**Pourquoi un script de mesure :** une fonctionnalité doit être démontrable. Sans mesure, les 4 causes ne seraient que des hypothèses ; le script donne un chiffre à chacune.

### 11.2 `scripts/mesurer_limites.py [JOURNAL] [N ...]`

- Par défaut : échantillon, N = 1 2 4 8. Appelle les **vraies** fonctions de P2 (`calculer_blocs`, `lire_lignes`, `analyser_bloc`, `fusionner`) sans les modifier, comme `demontrer_p4.py`.
- Mesures :
  - **disque :** lecture seule par morceaux de 16 Mo, puis lecture + décodage en lignes, dans le principal ;
  - **création des processus :** « Pool vide » (créer N workers, une tâche vide chacun, arrêter) ;
  - **cœurs :** dans chaque worker, `time.perf_counter()` (temps écoulé) **et** `time.process_time()` (temps de calcul donné par le noyau). Si le worker attend un cœur ou le disque, le temps écoulé dépasse le temps de calcul ;
  - **partie non parallélisable :** découpage, surcoût du Pool (phase parallèle − worker le plus long), fusion, et taille des résultats renvoyés (`len(pickle.dumps(res))`, ce que le Pool recopie).
- Vérifie que chaque N a analysé toutes les lignes. Écrit sur stdout ; on redirige vers `resultats/`.
- Codes : 0 = OK ; 1 = fichier absent / illisible (ou nombre de lignes différent) ; 2 = N invalide.

### 11.3 Résultats sur `access.log` (Mac, 27/10, une exécution)

| N | Pool vide | Total | CPU total | Worker : écoulé / calcul | Part non parallèle |
| --- | --- | --- | --- | --- | --- |
| 1 | 0,45 s | 36,8 s | 33,3 s | 36,7 / 33,3 (91 %) | 0,4 % |
| 2 | 0,25 s | 21,2 s | 40,3 s | 21,0 / 20,2 (96 %) | 0,8 % |
| 4 | 0,36 s | 34,3 s | 82,9 s | 33,9 / 20,7 (61 %) | 0,8 % |
| 8 | 0,53 s | 29,5 s | 85,0 s | 28,5 / 10,6 (37 %) | 2,2 % |

Lecture seule à froid : **26,6 s (70 Mo/s)** ; lecture + décodage (en cache) : 16,9 s.

### 11.4 Ce qu'il faut savoir expliquer

- **Cœurs (cause principale) :** 2 cœurs physiques. À N = 4, le CPU total **double** pour le même travail : les 2 threads hyperthreading d'un cœur se partagent ses unités de calcul. À N = 8, un worker ne calcule que 37 % du temps, il attend son tour (ordonnanceur, changements de contexte).
- **Fréquence :** de N = 1 à N = 2, +21 % de CPU pour le même travail. Seul, un cœur monte en Turbo Boost (jusqu'à 3,6 GHz d'après la fiche Intel, non mesuré) ; à deux, ils sont limités par les 7 W et la chaleur (MacBook Air sans ventilateur). 2 ÷ 1,21 ≈ x1,65, proche du x1,60 mesuré entre 1 et 2 workers en P6.
- **Création des processus :** 0,25 à 0,53 s (`spawn` : nouvel interpréteur qui réimporte nos modules). Négligeable sur 9 M lignes, dominant sur l'échantillon (part non parallèle 26 à 68 %) : c'est pour ça que P2 est plus lent que P1 sur l'échantillon.
- **Disque :** le dépôt est sur le **partage NFS d'OrbStack** (`mount` → `OrbStack:/OrbStack … (nfs)`). À froid, lire 1,86 Go prend 26,6 s : **quel que soit N**, on ne descend pas en dessous. En cache c'est rapide, d'où les 1ers essais P6 plus lents. Même en cache, 1 worker attend 3,4 s. Hypothèse non mesurée : le serveur NFS d'OrbStack prend du CPU et concurrence les workers à N = 4.
- **Amdahl :** `S(N) = 1 / (f + (1 − f) / N)`. Notre `f` mesurée = 0,4 à 2,2 % → jusqu'à x6,9 possible avec 8 vrais cœurs. Donc **ce n'est pas le code qui limite, c'est le matériel**. `f` grandit avec N (résultats renvoyés : 116 → 887 ko, car chaque worker renvoie ses propres Counter).
- **À retenir :** le meilleur N = nombre de **cœurs physiques**. Notre N par défaut (`os.cpu_count()` = cœurs logiques = 4) n'est donc pas optimal sur ce Mac (amélioration possible, non faite).
- **Honnêteté :** une seule exécution (N = 4 plus lent que N = 8 ici, l'inverse en P6) ; les accélérations de référence restent celles de P6.

### 11.5 Vérifications (27/10)

| Vérification | Résultat |
| --- | --- |
| Échantillon, N = 1 2 4 8 | Code 0, 100 000 lignes pour chaque N ✅ |
| Lancé depuis `/` | Code 0 ✅ |
| Fichier absent / dossier / N = `0` / N = `abc` | Codes 1 / 1 / 2 / 2, messages clairs ✅ |
| `access.log` (lancé par Louis, Mac) | Code 0, 9 000 000 lignes pour chaque N ✅ |
| Chiffres de `limites_P7.md` recalculés depuis `limites_access.txt` et `mesures_p2_access.txt` | Cohérents ✅ |

### 11.6 Comment lancer

```bash
python3 scripts/mesurer_limites.py                          # échantillon (quelques secondes)
python3 scripts/mesurer_limites.py data/access.log > resultats/limites_access.txt   # ~3 min
```

---

## 12. Rapport de performance (PDF)

### 12.1 Ce qui était demandé

| Livrable (sujet) | Fait | Où |
| --- | --- | --- |
| Code et rapport de performance : code source commenté, versions séquentielle et parallèle, script de test, tableau et graphique des temps, analyse (P1 à P10), **PDF, 6 pages max** | ✅ 6 pages | `docs/rapport_performance.pdf` |

### 12.2 Contenu, page par page

| Page | Contenu |
| --- | --- |
| 1 | Page de garde complète (choix de Louis), avec un encadré résumé (9 M lignes, rapports identiques, x1,44). Champs **surlignés en jaune** à compléter : équipe, chef de projet, noms |
| 2 | Tableau de couverture P1–P10 (section, commande de démo, état ; P8 et P10 « Non réalisé ») + 1. Le programme : 3 modules partagés, découpage en blocs recalés sur `\n`, lecture par morceaux de 16 Mo, chronomètre |
| 3 | 2. P3 (sortie réelle de `tester_p2.sh` sur l'échantillon + résultat sur `access.log`) ; 3. P6 : machine, méthode (3 essais entrelacés, médiane), tableau, **graphique SVG** |
| 4 | 4. P4 : inventaire condensé, sortie réelle de `demontrer_p4.py`, contre-épreuve threads, contre-exemple `Manager().dict()` + `Lock` ; 5. P5 : graphe de Holt, tableau des 4 conditions de Coffman, attentes sans fin possibles |
| 5 | 6. P7 : tableau de décomposition, les 4 causes, Amdahl, synthèse |
| 6 | 7. P9 : règle des lignes mal formées, fichier de test (1 analysée, 5 ignorées), erreurs réelles et codes de retour ; 8. Limites (P8 / P10 non réalisés, N par défaut, NFS, une seule exécution P7, worker tué) ; encadré « Usage d'un outil d'IA » |

### 12.3 Choix techniques (à savoir expliquer)

- **Même méthode que le dossier d'architecture** (source HTML + Chrome headless) et même CSS : les deux livrables se ressemblent.
- **`generer_pdf.sh` généralisé** : argument facultatif `NOM` (`dossier_architecture` par défaut, ou `rapport_performance`). Un `case` n'accepte que ces deux noms et fixe la limite de pages du sujet (10 ou 6) pour l'avertissement. *Pourquoi une liste fermée :* l'avertissement reste juste pour chaque livrable, et une faute de frappe donne « livrable inconnu » (code 2) au lieu de « fichier introuvable ».
- **Graphique inclus par chemin relatif** (`<img src="../resultats/graphique_p2_access.svg">`) : pas de copie, toujours à jour si on relance `tracer_graphique.py`, et vectoriel dans le PDF.
- **Sorties réelles** relancées le 27/10 sur l'échantillon (`tester_p2.sh`, `demontrer_p4.py`, cas d'erreur de `analyse_par.py`, fichier de test de 6 lignes dans le scratchpad).
- **Honnêteté :** seules les mesures du Mac servent à l'accélération (le P1 de la VM, 59,8 s, est cité comme non comparable) ; la phrase sur P8 (GIL) est présentée comme une **prévision**, pas une mesure.
- Choix de Louis : source et PDF **non versionnés**, comme le dossier d'architecture (`.gitignore`).

### 12.4 Vérifications réalisées (27/10, Mac)

| Vérification | Résultat |
| --- | --- |
| `generer_pdf.sh rapport_performance` | PDF écrit, **6 pages**, code 0 ✅ |
| `generer_pdf.sh` sans argument, depuis la racine et depuis `/` | Dossier d'architecture, code 0 ✅ |
| `generer_pdf.sh inconnu` / `a b` / `CHROME=/nexiste/pas` | Codes 2 / 2 / 1, messages clairs ✅ |
| Relecture des 6 pages en image (PDFKit) | Pas de texte coupé ni de titre orphelin (alignement de la sortie P9 corrigé) ✅ |
| Contrôle automatique des nombres du rapport par rapport à `mesures_p2_access.txt` et `limites_access.txt` | 46 / 46 présents ; valeurs dérivées recalculées (+21 %, x1,65, x1,60, 91/96/61/37 %, 3,4 s, x6,9) ✅ |
| Dossier d'architecture après ajout de `mesurer_limites.py` (arbre + récapitulatif) | 10 pages (limite), relu ✅ |

### 12.5 Comment lancer

```bash
bash scripts/generer_pdf.sh rapport_performance   # -> docs/rapport_performance.pdf
bash scripts/generer_pdf.sh                       # -> docs/dossier_architecture.pdf
```

---

## 13. P8 — Processus ou threads ?

### 13.1 Ce qui était demandé

| # | Demande (sujet) | Fait | Où |
| --- | --- | --- | --- |
| P8 (Attendu) | Mesurer la même analyse avec des threads puis avec des processus, et expliquer l'écart observé | ✅ PC (WSL) ; Mac à faire | `src/analyse_threads.py`, `scripts/mesurer_p8.sh`, `docs/threads_P8.md`, `resultats/mesures_p8_access_linux.txt/.csv` |

**Changement de machine :** depuis le 28/10, le travail se fait sur un PC portable Windows + **WSL2**
(AMD Ryzen 7 5800H, **8 cœurs physiques / 16 logiques**, Python 3.12.3, dépôt sur le disque ext4 de WSL).
P6 et P7 ont été mesurées sur le Mac (2 cœurs) : les chiffres de P8 se comparent entre eux, pas avec P6.
Les sources HTML / PDF des livrables et `generer_pdf.sh` (non versionnés) sont restés sur le Mac.

### 13.2 `src/analyse_threads.py` — la même analyse avec des threads

- Même interface que P2 (`JOURNAL [N]`), mêmes messages, mêmes codes de retour, même chronomètre.
- **Une seule différence avec P2 :** `ThreadPool(processes=n)` (de `multiprocessing.pool`) au lieu de `Pool(processes=n)`.
  `ThreadPool` a la même interface (`starmap`), ses workers sont des threads du même processus.
- `calculer_blocs`, `analyser_bloc` et `lire_nombre_workers` sont **importés** de `analyse_par.py` (pas copiés) :
  c'est donc vraiment « la même analyse ». Importer `analyse_par` ne lance pas P2, grâce à son `if __name__ == "__main__":`.
- Pas de verrou : chaque thread crée ses propres `Counter` dans `analyser_bloc` et les renvoie ; fusion après `starmap` (comme P4).

### 13.3 `scripts/mesurer_p8.sh JOURNAL [ESSAIS]`

- Même modèle que `mesurer.sh` : versions `seq`, `t1 t2 t4 t8` (threads), `p1 p2 p4 p8` (processus), 3 essais
  entrelacés, médianes, accélération, machine décrite (Linux et macOS).
- En plus du « Temps d'analyse » : temps **CPU** (user + sys, `time` de bash avec `TIMEFORMAT="%U %S"`) et temps
  **réel** sur l'horloge monotone → **cœurs occupés = CPU ÷ réel**. C'est la mesure qui montre le GIL.
- Chaque rapport est comparé au séquentiel (`diff`, hors temps) : un seul différent → arrêt, code 1.
- Sortie `resultats/mesures_p8_NOM_SYS.txt/.csv`, `SYS` = `linux` ou `macos` : les deux machines ne s'écrasent pas.
- Codes : 0 = OK ; 1 = fichier absent / dossier / illisible, version en échec ou rapport différent ; 2 = mauvaise utilisation.

**Piège rencontré (à savoir raconter) :** la 1re mesure prenait le temps réel du `time` de bash. Plusieurs essais avaient
un temps réel **plus petit** que le temps d'analyse (15,48 s pour 17,80 s), toujours d'environ 2,3 s. Cause : WSL
recale son **horloge murale** sur Windows (saut de −2,4 s relevé pendant un test de 45 s comparant `time.time()`
et `time.monotonic()`). Le `time` de bash utilise l'horloge murale ; `time.perf_counter()` (nos programmes) est
monotone, donc les temps d'analyse et accélérations étaient justes. Correction : `horloge()` lit
`time.monotonic()`. Mesure relancée : 27 essais, 0 anomalie. Anciennes mesures gardées hors dépôt (scratchpad).

### 13.4 Résultats (`access.log`, PC WSL, 28/10/2026 13:25, médianes de 3 essais)

| Version | Temps | Accélération | CPU | Cœurs occupés |
| --- | --- | --- | --- | --- |
| Séquentiel | 18,597 s | x1,00 | 17,25 s | 0,93 |
| 1 / 2 / 4 / 8 threads | 20,433 / 21,204 / 21,734 / 22,037 s | x0,91 / x0,88 / x0,86 / **x0,84** | 18,91 → 21,37 s | 0,92 → **0,97** |
| 1 / 2 / 4 / 8 processus | 19,130 / 10,719 / 5,993 / 4,282 s | x0,97 / x1,73 / x3,10 / **x4,34** | 17,76 → 30,31 s | 0,93 / 1,81 / 3,60 / **7,09** |

### 13.5 Ce qu'il faut savoir expliquer

- **GIL** (*Global Interpreter Lock*) : dans CPython, un seul thread par processus exécute du code Python à la fois.
  Il est relâché pendant les entrées / sorties et toutes les 5 ms (`sys.getswitchinterval()`).
- **Threads :** notre travail est du calcul Python (`split`, `isdigit`, `Counter`) → les threads calculent **à tour de
  rôle** : 0,97 cœur occupé avec 8 threads. Ils existent bien (`ps` : 1 processus, 12 threads), mais ne travaillent pas en même temps.
- **Threads un peu plus lents que le séquentiel :** le CPU monte de 18,91 à 21,37 s de 1 à 8 threads = coût des passages
  de relais du GIL (réveil d'un thread, cache). Sys de 2,0 à 3,1 s : *hypothèse non vérifiée* = appels `futex`.
- **Processus :** un interpréteur et **un GIL par processus** → 7,09 cœurs occupés avec 8, x4,34. Pas x8 : CPU
  17,76 → 30,31 s (cache et mémoire partagés, fréquence plus basse avec 8 cœurs actifs) + parties non parallélisables (P7).
- **Quand les threads servent :** entrées / sorties (réseau, disque lent), code C qui relâche le GIL, Python 3.13
  « free-threaded » sans GIL (non testé, non installé).
- **Lien P4 :** threads = mémoire partagée → un `Counter` commun serait une vraie section critique (`+= 1` n'est pas
  atomique, le GIL peut changer de thread au milieu) ; notre conception l'évite (un `Counter` par thread).

### 13.6 Vérifications (28/10, PC WSL)

| Vérification | Résultat |
| --- | --- |
| `analyse_threads.py` échantillon, N = 1, 2, 4, 8 : `diff` avec P1 hors temps | IDENTIQUE ✅ |
| Sans argument / 3 arguments / absent / dossier / N = `0`, `-3`, `abc` / fichier vide / depuis `/` | Codes 2 / 2 / 1 / 1 / 2 / 0 / 0 ✅ |
| `ps` pendant `analyse_threads.py … 8` | 1 processus, 12 threads, 0 fils ✅ |
| `mesurer_p8.sh` échantillon (3 essais) ; erreurs (sans arg, 3 args, absent, dossier, illisible, ESSAIS `0` / `abc`) ; depuis `/` | Code 0 ; codes 2 / 2 / 1 / 1 / 1 / 2 / 2 ; code 0 ✅ |
| Contre-épreuve : copie avec une version threads faussée (1 ligne en moins) | « diffère du séquentiel », code 1 ✅ |
| `access.log` (lancé par Louis) | 27 rapports identiques au séquentiel, réel ≥ temps d'analyse pour les 27 essais ✅ |

### 13.7 Comment lancer

```bash
python3 src/analyse_threads.py data/echantillon_access.log 4    # rapport avec 4 threads
bash scripts/mesurer_p8.sh data/echantillon_access.log 1          # essai rapide (puis supprimer les fichiers _echantillon_)
bash scripts/mesurer_p8.sh data/access.log                        # mesure officielle (~10 min sur le PC, plus sur le Mac)
```

---

## 14. Prochaines étapes

Point d'avancement n°3 le **mercredi 28 octobre** (toutes les fonctionnalités « Indispensable » démontrées), dépôt le **jeudi 29 à 12h30**.

1. ~~P3 et P6 sur le fichier complet~~ : faits le 26/10 sur le Mac (voir 5.1).
2. ~~P6 : graphique~~ : fait le 26/10 (`resultats/graphique_p2_access.svg`, voir 6.3 étape 6). **P6 est complète** : 3 essais × 5 versions sur le fichier complet, tableau, graphique, accélération, machine décrite (processeur, cœurs physiques / logiques).
3. ~~P4 / P5~~ : faits le 26/10 (`docs/concurrence_P4_P5.md`, `scripts/demontrer_p4.py`, voir section 7). À reprendre dans le PDF du rapport de performance.
4. ~~Scripts Bash A2 à A8~~ : faits le 27/10 (voir section 8). **À faire par Louis :** `time bash scripts/controle.sh data/access.log` puis comparer à `resultats/rapport_seq.txt`, et versionner `resultats/controle_access.txt`.
5. ~~A6 — schéma en couches~~ : fait le 27/10 (voir section 9). **À faire par Louis :** relancer `bash scripts/installer.sh` dans la VM pour mettre `tracer_appels.sh` au groupe `paralog` (il est en 750 mais au groupe `louis`). **Toutes les fonctionnalités « Indispensable » d'architecture et de programmation sont faites** : prêt pour le point n°3.
6. ~~Dossier d'architecture (PDF)~~ : fait le 27/10 (`docs/dossier_architecture.pdf`, 9 pages, voir section 10). **À faire par Louis :** compléter la page de garde (champs surlignés en jaune dans le `.html` : équipe, chef de projet, noms) puis `bash scripts/generer_pdf.sh` ; relire l'encadré « Usage d'un outil d'IA » ; relancer `bash scripts/installer.sh` dans la VM (met les nouveaux fichiers en 640/750 au groupe `paralog`).
7. ~~P7~~ : fait le 27/10 (`docs/limites_P7.md`, `scripts/mesurer_limites.py`, voir section 11). **À faire par Louis :** relancer `bash scripts/installer.sh` dans la VM (met les 3 nouveaux fichiers au groupe `paralog`).
8. ~~PDF du rapport de performance~~ : fait le 27/10 (`docs/rapport_performance.pdf`, 6 pages, voir section 12). `mesurer_limites.py` ajouté au dossier d'architecture (désormais 10 pages). **À faire par Louis :** compléter la page de garde des deux `.html` (champs jaunes) puis `bash scripts/generer_pdf.sh rapport_performance` et `bash scripts/generer_pdf.sh` ; relire les encadrés « Usage d'un outil d'IA ».
9. ~~P8 (Attendu, pas Bonus)~~ : fait le 28/10 sur le PC WSL (voir section 13). **À faire par Louis :**
   - sur le Mac : récupérer `src/analyse_threads.py` et `scripts/mesurer_p8.sh`, lancer `bash scripts/mesurer_p8.sh data/access.log` (→ `resultats/mesures_p8_access_macos.*`), puis ajouter ses chiffres à `docs/threads_P8.md` ;
   - dans `docs/rapport_performance.html` (sur le Mac) : P8 « Non réalisé » → « Fait », ajouter un résumé de `threads_P8.md` (tableau + GIL), en condensant pour rester à **6 pages**, puis `bash scripts/generer_pdf.sh rapport_performance` ; ajouter `analyse_threads.py` et `mesurer_p8.sh` à l'arborescence du dossier d'architecture (attention, déjà à 10 pages) ;
   - relancer `bash scripts/installer.sh` (droits et groupe des nouveaux fichiers).
10. **Prochaine étape : gestion de projet** G1 à G6 (dossier PDF, 12 pages max, **Indispensable**) : note de cadrage, backlog / WBS / RACI, PERT et Gantt, registre des risques, Kanban et comptes rendus des 3 points, REX.
11. Bonus si le temps le permet : A9 (relevé `ps` / `top` pendant une exécution ; `ps -o pid,nlwp` déjà utilisé pour P8), P10 (producteur / consommateur), G9 (éthique et sobriété).

---

## Journal des modifications

| Date | Changement |
| --- | --- |
| 2026-10-19 | P1 : création de `analyse_commun.py`, `rapport.py` et `analyse_seq.py`. Vérifications sur l'échantillon. |
| 2026-10-19 | Règle des lignes mal formées adaptée après la réponse de l'encadrant : ajout du contrôle de l'IP, retrait du contrôle des guillemets. |
| 2026-10-19 | Création de ce document de compréhension. |
| 2026-10-19 | `.gitignore` : ajout de `COMPREHENSION.md`, pour que ce document reste local et ne soit pas versionné. |
| 2026-10-19 | `access.log` généré (9 M lignes, ~1,86 Go, bien ignoré par git). 1er essai P1 : 79,160 s, rapport de référence dans `resultats/rapport_seq.txt` (codes et heures = 9 000 000, 0 ignorée). |
| 2026-10-19 | Mesures P1 complétées : essais 2 (61,662 s) et 3 (59,849 s) dans la VM Ubuntu, rapports identiques à la référence. Médiane : **59,849 s**. Le 1er essai à 79,160 s est écarté (voir section 5). |
| 2026-10-19 | Création de `resultats/mesures_p1.txt` (versionné) : les 3 temps P1 et la médiane, pour qu'ils soient visibles dans le dépôt. |
| 2026-10-26 | P2, étapes 1 à 3 : création de `src/analyse_par.py` (découpage en blocs recalés sur les `\n`, workers `multiprocessing.Pool` lisant par morceaux de 16 Mo, fusion, rapport, N optionnel = nombre de cœurs). Fusion des workers = résultat P1 pour N = 1, 2, 4, 8. |
| 2026-10-26 | P2, étape 4 : création de `scripts/tester_p2.sh` (diff P1 / P2 pour N = 1, 2, 4, 8, couvre P3). Échantillon : identique pour tous les N. Cas limites (fichier vide, lignes mal formées, octet invalide, dernière ligne sans `\n`) : identiques. |
| 2026-10-26 | P2, étape 5 : création de `scripts/mesurer.sh` (3 essais entrelacés, médianes, accélération, description de la machine, sortie `.txt` + `.csv`). Testé sur l'échantillon ; mesure officielle sur `access.log` à lancer dans la VM. |
| 2026-10-26 | Mise à jour de ce document : sections 1, 2, 4.2, 5, nouvelle section 6 (P2 détaillée) et section 7 (prochaines étapes). |
| 2026-10-26 | P3 sur `access.log` (Mac) : rapports P2 identiques à P1 pour N = 1, 2, 4, 8. P6 : `mesurer.sh` sur `access.log` (Mac, i5-8210Y 2 cœurs physiques / 4 threads) → P1 34,534 s ; P2 N=1 38,239 s (x0,90), N=2 23,962 s (**x1,44**), N=4 27,949 s (x1,24), N=8 30,136 s (x1,15). Nouvelle section 5.1 avec l'interprétation (cœurs physiques vs hyperthreading, surcoût, Amdahl). |
| 2026-10-26 | P6 terminée : création de `scripts/tracer_graphique.py` (graphique SVG sans matplotlib : temps médian + essais, accélération mesurée vs idéale) → `resultats/graphique_p2_access.svg`. `mesurer.sh` décrit les cœurs physiques et logiques ; ligne Machine de `mesures_p2_access.txt` corrigée à la main (2 physiques, 4 logiques). Sections 1, 2, 5.1, 6.1, 6.3 (étapes 5 et 6), 6.4 et 7 mises à jour. |
| 2026-10-26 | P4 / P5 : création de `docs/concurrence_P4_P5.md` (inventaire des données, aucune section critique ; 4 conditions de Coffman, graphe ressources / processus, limites) et de `scripts/demontrer_p4.py` (preuve à l'exécution : PID distincts, variable globale à 0 dans le principal, fusion = séquentiel ; contre-épreuve avec threads). Vérifié : Pool qui attend sans fin si un worker est tué (Python 3.15). Nouvelle section 7, sections 1, 2, 6.2 et 8 mises à jour. |
| 2026-10-27 | Section 4.3 : trois phrases qui parlaient de P2 au futur mises au présent ; la phrase « P2 devra mesurer exactement la même chose » corrigée (le chronomètre de P2 compte en plus le découpage, la création des workers et la fusion). |
| 2026-10-27 | Scripts Bash A2–A8 : création de `installer.sh` (A2 + A3), `lancer.sh` (A4), `controle.sh` (A5, indicateurs 1 et 2), `nettoyer.sh` (A7), `archiver.sh` (A8) et de `docs/droits_A3.md` (tableau des droits + preuve). `.gitignore` : rapports de `lancer.sh` et archives exclus. VM : groupe `paralog`, utilisateurs de test `coequipier` / `exterieur` (gardés pour la démo). `installer.sh` appliqué au dépôt (3 scripts passés en mode 755). Nouvelle section 8, sections 1, 2 et 9 (prochaines étapes, prochaine : A6) mises à jour. |
| 2026-10-27 | A6 : création de `docs/schema_A6.md` (schéma en couches ASCII, trace réelle, tableau de 8 appels système, points à expliquer), `docs/schema_A6.svg` (schéma dessiné pour le PDF) et `scripts/tracer_appels.sh` (relevé `strace -f -ff` de `lancer.sh` résumé par processus). `strace` installé dans la VM. Vérifié : EACCES pour `exterieur` à `openat`. Nouvelle section 9, sections 1, 2, sommaire et prochaines étapes (devenue section 10) mises à jour. |
| 2026-10-27 | Dossier d'architecture : création de `docs/dossier_architecture.html` (source, CSS d'impression A4), `docs/dossier_architecture.pdf` (9 pages : couverture A1–A9, présentation, arborescence A1, schéma A6, droits A3, mode d'emploi des scripts avec sorties réelles sur l'échantillon, limites, usage de l'IA) et `scripts/generer_pdf.sh` (Chrome headless, sans chemin en dur). Nouvelle section 10, sections 1, 2, sommaire et prochaines étapes (devenue section 11, prochaine : P7) mises à jour. |
| 2026-10-27 | `.gitignore` : ajout de `docs/dossier_architecture.html`, `docs/dossier_architecture.pdf` et `scripts/generer_pdf.sh` (choix de Louis : non versionnés). Section 2 mise à jour. |
| 2026-10-27 | P7 : création de `scripts/mesurer_limites.py` (décompose le temps de P2 : lecture disque, Pool vide, temps écoulé / CPU de chaque worker, découpage, surcoût, fusion, taille des résultats), de `resultats/limites_access.txt` (mesure sur `access.log`, Mac) et de `docs/limites_P7.md`. Conclusions : partie non parallélisable du code 0,4–2,2 % ; limites = 2 cœurs physiques (hyperthreading : CPU ×2 à N = 4), baisse de fréquence (+21 % CPU à N = 2), lecture à froid sur le partage NFS d'OrbStack (26,6 s). Nouvelle section 11 ; sommaire, sections 1, 2, 5.1, 6.5 et prochaines étapes (devenue section 12, prochaine : PDF du rapport de performance) mises à jour. |
| 2026-10-27 | Rapport de performance : création de `docs/rapport_performance.html` et `.pdf` (6 pages : garde, couverture P1–P10, programme, P3, P6 avec tableau et graphique, P4, P5, P7, P9, limites, usage de l'IA). `scripts/generer_pdf.sh` généralisé (argument `NOM`, limite de pages par livrable). Dossier d'architecture : `mesurer_limites.py`, `limites_access.txt`, `limites_P7.md` et le rapport ajoutés (arbre + récapitulatif), 10 pages. `.gitignore` : source et PDF du rapport non versionnés. Nouvelle section 12 ; sommaire, sections 1, 2, 10.5 et prochaines étapes (devenue section 13, prochaine : gestion de projet) mises à jour. |
| 2026-10-28 | P8 : création de `src/analyse_threads.py` (même analyse que P2 avec `ThreadPool`, fonctions importées de P2), `scripts/mesurer_p8.sh` (threads vs processus N = 1, 2, 4, 8, 3 essais, cœurs occupés = CPU ÷ réel, `diff` de chaque rapport) et `docs/threads_P8.md`. Mesure `access.log` sur le PC WSL (Ryzen 7 5800H, 8 cœurs) → `resultats/mesures_p8_access_linux.*` : 8 threads x0,84 / 0,97 cœur (GIL), 8 processus x4,34 / 7,09 cœurs. Saut d'horloge de WSL (−2,4 s) détecté et corrigé (temps réel sur l'horloge monotone), mesure relancée. Nouvelle section 13 ; sommaire, en-tête (document désormais versionné), sections 1, 2 et prochaines étapes (devenue section 14) mises à jour. |
