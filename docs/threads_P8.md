# ParaLog — Processus ou threads ? (P8)

Ce document fait partie du rapport de performance. Il compare la même analyse faite par N **threads**
puis par N **processus**, et explique l'écart observé. Il répond au critère P8 du sujet.

## 1. Critère du sujet et méthode

> Vous mesurez la même analyse avec des threads puis avec des processus, et vous expliquez l'écart observé.

### 1.1 « La même analyse » : deux programmes qui ne diffèrent que d'une ligne

| Programme | Workers | Ligne qui crée les workers |
| --- | --- | --- |
| `src/analyse_par.py` (P2) | N **processus** | `with Pool(processes=n) as pool:` |
| `src/analyse_threads.py` (P8) | N **threads** d'un seul processus | `with ThreadPool(processes=n) as pool:` |

`analyse_threads.py` **importe** de P2 le découpage (`calculer_blocs`), le travail d'un worker (`analyser_bloc`)
et la lecture de N (`lire_nombre_workers`), sans les copier ni les modifier. `ThreadPool` a la même interface que
`Pool` (`starmap`). Les deux programmes ont les mêmes arguments, les mêmes messages, les mêmes codes de retour et
le même chronomètre. Le seul paramètre qui change est donc : **threads ou processus**.

Comme en P2, chaque thread crée ses propres `Counter` et les renvoie ; la fusion est faite après `starmap`.
Aucune donnée n'est modifiée par deux threads : pas de section critique, pas de verrou (même raisonnement que P4).

### 1.2 Le script de mesure : `scripts/mesurer_p8.sh`

```bash
bash scripts/mesurer_p8.sh data/access.log      # -> resultats/mesures_p8_access_linux.txt et .csv
```

- Versions : séquentiel (référence), puis 1, 2, 4 et 8 threads, puis 1, 2, 4 et 8 processus.
  **3 essais entrelacés** (essai 1 de chaque version, puis essai 2…), **médiane**.
- Pour chaque lancement :
  - le **temps d'analyse** affiché par le programme (même mesure qu'en P6) ;
  - le **temps CPU** (user + sys) donné par la commande `time` de bash ;
  - le **temps réel** de la commande, lu sur une horloge monotone.
- **Cœurs occupés = temps CPU ÷ temps réel** : le nombre moyen de cœurs qui ont réellement calculé en même temps.
  C'est la mesure qui explique l'écart.
- Chaque rapport est comparé à celui du séquentiel avec `diff` (hors temps). Si un seul diffère, le script
  s'arrête (code 1). Les 27 rapports de la mesure officielle sont identiques.
- Le nom du fichier contient le système (`linux`, `macos`) : les mesures de deux machines ne s'écrasent pas.

**Machine :** PC portable, AMD Ryzen 7 5800H, **8 cœurs physiques, 16 cœurs logiques**, Windows avec WSL2
(Linux 6.6), Python 3.12.3. Mesure du 28/10/2026, dépôt sur le disque Linux de WSL.
Ce n'est pas la machine de P6 / P7 (MacBook Air, 2 cœurs) : les chiffres de P8 se comparent entre eux,
pas avec ceux de P6.

## 2. Résultats (`resultats/mesures_p8_access_linux.txt`)

Fichier complet, 9 000 000 lignes, médianes de 3 essais :

| Version | Temps d'analyse | Accélération | Temps CPU | Cœurs occupés |
| --- | --- | --- | --- | --- |
| Séquentiel | 18,597 s | x1,00 | 17,25 s | 0,93 |
| 1 thread | 20,433 s | x0,91 | 18,91 s | 0,92 |
| 2 threads | 21,204 s | x0,88 | 20,07 s | 0,94 |
| 4 threads | 21,734 s | x0,86 | 20,69 s | 0,95 |
| 8 threads | 22,037 s | **x0,84** | 21,37 s | **0,97** |
| 1 processus | 19,130 s | x0,97 | 17,76 s | 0,93 |
| 2 processus | 10,719 s | x1,73 | 19,54 s | 1,81 |
| 4 processus | 5,993 s | x3,10 | 21,80 s | 3,60 |
| 8 processus | 4,282 s | **x4,34** | 30,31 s | **7,09** |

Accélération = temps séquentiel ÷ temps de la version.

**Le constat :**
- avec des **threads**, plus on en met, plus c'est **lent** (x0,91 → x0,84), et on n'occupe **jamais plus d'un cœur** ;
- avec des **processus**, le temps est divisé par **4,3** avec 8 workers, et **7 cœurs** calculent en même temps.

## 3. Explication : le GIL

### 3.1 Ce qu'est le GIL

L'interpréteur Python standard (CPython) a un **verrou global**, le GIL (*Global Interpreter Lock*) :
dans un processus, **un seul thread à la fois** peut exécuter du code Python. Les autres threads attendent
d'avoir le verrou. Il protège les structures internes de l'interpréteur (par exemple le compteur de
références de chaque objet), qui ne sont pas prévues pour être modifiées par deux threads en même temps.

Le GIL est relâché :
- quand un thread fait une **entrée / sortie** (`read()` d'un fichier, attente réseau) ;
- toutes les **5 ms** (`sys.getswitchinterval()` = 0,005), pour laisser une chance aux autres threads.

### 3.2 Pourquoi les threads ne vont pas plus vite

Notre travail est presque entièrement du **calcul en Python** : `split()`, `isdigit()`, `count()`,
`Counter[...] += 1`, 9 millions de fois. Seule la lecture du fichier relâche le GIL, et elle est courte
(fichier en cache, gros morceaux de 16 Mo).

Avec 8 threads, les 8 threads existent bien (vérifié avec `ps` : 1 seul processus, 12 threads), mais ils
**calculent à tour de rôle** : le temps CPU total reste celui d'**un seul cœur** (0,92 à 0,97 cœur occupé).
Le travail n'est pas réparti, il est seulement **découpé en tranches** de 5 ms.

### 3.3 Pourquoi les threads vont même un peu moins vite

Le temps CPU augmente avec le nombre de threads, pour le même travail : **18,91 s → 21,37 s** de 1 à 8 threads.
Ce surplus est le **coût des passages de relais** du GIL : toutes les 5 ms, le thread qui calcule doit rendre le
verrou, un autre doit être réveillé par le noyau et récupérer ses données en mémoire cache.
Le temps système (sys) passe d'ailleurs de 2,0 s à 3,1 s (médianes du `.csv`). *Hypothèse non vérifiée :* ce sont
les appels système qui endorment et réveillent les threads en attente du GIL (`futex` sous Linux).

### 3.4 Pourquoi les processus vont plus vite

Chaque processus a **son propre interpréteur, donc son propre GIL**. Les N workers ne s'attendent jamais :
le noyau les répartit sur N cœurs différents, et le temps CPU est vraiment fait **en même temps**
(1,81 cœur occupé pour 2 processus, 3,60 pour 4, 7,09 pour 8).

Le gain n'est pas x8 avec 8 processus, pour les raisons de P7 (voir `docs/limites_P7.md`) :
- le temps CPU total augmente (17,76 s → 30,31 s de 1 à 8 processus) : les 8 cœurs se partagent la mémoire cache
  et l'accès à la mémoire, et le processeur baisse sa fréquence quand tous ses cœurs travaillent ;
- il reste des parties non parallélisables : démarrage des processus, renvoi des `Counter` par copie, fusion.

### 3.5 Résumé de l'écart

| | Threads | Processus |
| --- | --- | --- |
| Mémoire | Partagée (un seul processus) | Séparée (un processus par worker) |
| GIL | **Un seul** pour tous les threads | **Un par processus** |
| Cœurs occupés (8 workers) | 0,97 | 7,09 |
| Accélération (8 workers) | x0,84 (plus lent que le séquentiel) | x4,34 |
| Coût de démarrage | Faible (un thread) | Plus élevé (un interpréteur par worker) |
| Renvoi des résultats | Aucune copie (même mémoire) | Copie des `Counter` (pickle) |

**Conclusion :** pour un travail de **calcul en Python** comme le nôtre, les threads n'apportent rien à cause du GIL ;
les **processus** sont le bon choix. C'est ce que fait P2.

## 4. Quand les threads seraient-ils utiles ?

- **Travail d'entrées / sorties** : télécharger des fichiers, attendre des réponses réseau, lire beaucoup de petits
  fichiers sur un disque lent. Pendant l'attente, le GIL est relâché, et les autres threads avancent.
- **Bibliothèques qui relâchent le GIL** pendant un calcul écrit en C (compression `zlib`, `hashlib` sur de gros blocs…).
- **Python sans GIL** : depuis Python 3.13, une version expérimentale « free-threaded » (`python3.13t`) existe.
  Les threads pourraient alors calculer en parallèle. *Non testé* : elle n'est pas installée sur nos machines.

## 5. Lien avec P4 (section critique)

Les threads **partagent la mémoire** : si tous les threads ajoutaient leurs comptes dans un `Counter` commun,
ce serait une vraie **section critique**. Le GIL ne la protège pas : `compteur[cle] += 1` se fait en plusieurs
instructions (lire, ajouter, écrire), et le GIL peut passer à un autre thread entre deux d'entre elles.
Il faudrait un `threading.Lock`, pris 9 millions de fois. Notre conception évite ce problème, comme en P2 :
chaque thread a ses propres `Counter`, la fusion est faite une seule fois à la fin, par le seul thread principal.
La contre-épreuve de P4 l'avait déjà montré : une copie de `scripts/demontrer_p4.py` avec des threads
(`multiprocessing.dummy.Pool`) voyait sa variable globale remplie par tous les workers (voir `docs/concurrence_P4_P5.md`).

## 6. Une difficulté de mesure rencontrée (WSL)

Première version du script : le temps réel était pris avec le `time` de bash. Dans plusieurs essais, il était
**plus petit que le temps d'analyse** mesuré dans le programme (ex. 15,48 s pour 17,80 s), ce qui est impossible,
et toujours d'environ 2,3 s. Cause trouvée : WSL recale régulièrement son **horloge murale** sur celle de Windows
(un saut de **−2,4 s** relevé pendant un test de 45 s). Le `time` de bash utilise cette horloge ; nos programmes
utilisent `time.perf_counter()`, une **horloge monotone**, qui ne recule jamais.

Correction : le script lit le temps réel sur l'horloge monotone (`time.monotonic()`). Mesure relancée :
27 essais, **0 anomalie** (temps réel toujours ≥ temps d'analyse). Les temps d'analyse et les accélérations
n'étaient pas touchés ; seule la colonne « cœurs occupés » l'était.
