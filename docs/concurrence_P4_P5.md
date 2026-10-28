# ParaLog — Concurrence : section critique (P4) et interblocage (P5)

Ce document fait partie du rapport de performance. Il porte sur la version parallèle
`src/analyse_par.py` (P2) et répond aux critères P4 et P5 du sujet.

Rappel du fonctionnement de P2 :

```
                          ┌─► worker 1 : analyser_bloc(chemin, 0,    b1)  ─┐
processus principal       ├─► worker 2 : analyser_bloc(chemin, b1,   b2)  ─┤
  calculer_blocs()  ──────┤   ...                                          ├──► fusionner() ──► rapport (stdout)
  (positions en octets)   └─► worker N : analyser_bloc(chemin, bN-1, fin) ─┘    (processus principal, après les workers)
```

---

## 1. P4 — Données partagées entre workers

### 1.1 Critère du sujet

> Vous identifiez chaque donnée partagée entre workers (compteur d'avancement, résultat commun,
> fichier de sortie…) et vous la protégez par un verrou. La section critique est la plus courte
> possible. **Si vous n'avez aucune donnée partagée, vous le démontrez.**

Une **section critique** est un morceau de code qui accède à une donnée partagée en écriture
par plusieurs processus ou threads. Sans verrou, deux écritures simultanées peuvent se perdre :
par exemple, deux workers lisent `total = 10`, ajoutent chacun 1 et écrivent tous les deux 11 au lieu de 12.

Notre programme n'a **aucune donnée partagée en écriture**, donc **aucune section critique**.
La démonstration se fait en deux temps : la lecture du code (1.2 et 1.3), puis une preuve à l'exécution (1.4).

### 1.2 Pourquoi les workers ne peuvent pas partager de mémoire

Les workers sont des **processus** (`multiprocessing.Pool`), pas des threads.
Chaque processus a son **propre espace mémoire** : une variable modifiée dans un worker
n'est visible ni par les autres workers ni par le processus principal.

- Sur macOS (méthode `spawn`) et sous Linux avec Python 3.14+ (méthode `forkserver`), chaque worker
  est un **nouvel interpréteur Python** qui réimporte le programme : il ne voit rien de la mémoire du parent.
- Avec `fork` (Linux, Python < 3.14), le worker démarre avec une **copie** de la mémoire du parent
  (copie à l'écriture) : ce qu'il modifie reste dans sa copie.

Pour partager de la mémoire entre processus, il faudrait le demander explicitement
(`multiprocessing.Value`, `Array`, `Manager`, `shared_memory`). Le code n'en utilise aucun :

```bash
grep -nE "Lock|Value|Array|Manager|Queue|shared_memory|global|threading" src/*.py
# -> seule réponse : "except ValueError" (une exception, pas un outil de partage)
```

### 1.3 Inventaire des données, une par une

| Donnée | Qui la lit / l'écrit | Partagée en écriture ? | Pourquoi (dans le code) |
| --- | --- | --- | --- |
| **Paramètres d'un worker** `(chemin, debut, fin)` | Écrits par le principal, lus par un seul worker | Non | Envoyés **par copie** au lancement (`pool.starmap`, `analyse_par.py:115`). Chaque worker a ses propres valeurs. |
| **Résultat commun** (les Counter des codes, IP, pages, heures) | Chaque worker crée **les siens** | Non | `analyser_lignes()` crée un résultat neuf (`resultats_vides()`, `analyse_commun.py`) dans la mémoire du worker. Il n'existe pas de Counter « global » que les workers rempliraient ensemble. |
| **Renvoi des résultats** | Worker → principal | Non | Chaque worker **renvoie** son dictionnaire (`return`, `analyse_par.py:78`). Il est copié (pickle) vers le principal. Aucun worker ne lit le résultat d'un autre. |
| **Fusion** | Le principal seul | Non | `fusionner()` est appelée **après** `pool.starmap`, qui ne rend la main que quand **tous** les blocs sont finis (`analyse_par.py:115-116`). Un seul processus, plus aucun worker actif. |
| **Compteur d'avancement** | — | N'existe pas | Pas de barre de progression ni de compteur commun. Les lignes analysées / ignorées sont comptées **dans chaque worker** puis additionnées à la fusion. |
| **Fichier de sortie** (rapport) | Le principal seul | Non | Le rapport est écrit sur stdout par `main()` (`analyse_par.py:126`), une seule fois, après la fusion. Les workers n'écrivent rien. |
| **stdout / stderr** | Le principal seul | Non | Tous les `print` de `analyse_par.py` sont dans `main()`. Les workers n'affichent rien, donc pas de messages entremêlés. |
| **Journal d'entrée** `access.log` | Tous les workers, **en lecture seule** | Non | Ouvert en `"rb"` (`analyse_par.py:56`). Lire en même temps un fichier qui ne change pas ne pose aucun problème. Chaque worker fait **son propre `open()`**, donc il a son propre descripteur et sa propre position (`seek`) : un worker qui avance ne déplace pas la position d'un autre. |
| **Zones lues dans le fichier** | Chaque worker lit son bloc | Non | Les blocs sont **disjoints** : `calculer_blocs()` donne des intervalles `[debut, fin)` contigus sans chevauchement (vérifié en P2). |
| **Constantes** `TAILLE_LECTURE`, `TAILLE_TOP` | Lues | Non | Entiers jamais modifiés. Une donnée qu'on ne fait que lire n'a pas besoin de verrou. |

**Point d'attention : les files internes du `Pool`.**
Pour envoyer les tâches et récupérer les résultats, `multiprocessing.Pool` utilise en interne des files
(tubes du système) protégées par ses propres verrous. Ces verrous sont dans la bibliothèque standard,
pris et relâchés par elle à chaque envoi : notre code ne les manipule jamais. C'est justement l'intérêt
d'utiliser `Pool` plutôt que de gérer nous-mêmes une file partagée.

### 1.4 Preuve à l'exécution

Le script `scripts/demontrer_p4.py` lance un vrai `Pool` avec **la vraie fonction `analyser_bloc()`** de P2.
Chaque tâche ajoute en plus le nombre de lignes de son bloc à une **variable globale** `LIGNES_VUES`,
puis renvoie son PID et la valeur de cette variable dans son processus.

```bash
python3 scripts/demontrer_p4.py                               # échantillon, 4 workers
python3 scripts/demontrer_p4.py data/echantillon_access.log 8
```

Résultat sur l'échantillon (Mac, 4 workers) :

```
Journal : data/echantillon_access.log, 4 workers, processus principal : PID 21396

PID worker            bloc (octets)  lignes du bloc  LIGNES_VUES dans ce worker
     21399            0-5148633               24948                       24948
     21398      5148633-10297292              24996                       24996
     21400     10297292-15445728              25034                       25034
     21401     15445728-20594286              25022                       25022

[OK] Blocs traités hors du processus principal : PID des workers [21398, 21399, 21400, 21401], principal 21396
[OK] LIGNES_VUES dans le processus principal = 0 (attendu : 0, car chaque worker modifie sa propre copie)
[OK] Somme des lignes des blocs = 100000, total séquentiel = 100000
[OK] Fusion des résultats des workers = résultat séquentiel
Conclusion : aucune donnée partagée entre les workers, donc aucune section critique.
```

Comment lire ce résultat :

- **4 PID différents, tous différents du principal :** chaque bloc est traité dans un processus à part.
- **`LIGNES_VUES` vaut 0 dans le principal,** alors que les workers y ont ajouté 100 000 lignes au total.
  Chaque worker a modifié **sa propre copie** de la variable : la mémoire n'est pas partagée.
- **Chaque worker ne voit que ses lignes** (24 948, 24 996…), et pas le cumul des autres.
- **La somme des blocs donne 100 000,** et la fusion est égale à l'analyse séquentielle.
  Les workers n'ont pas besoin de communiquer entre eux pour obtenir le bon résultat.

Même résultat avec 8 workers : 8 PID distincts, `LIGNES_VUES = 0` dans le principal.

**Contre-épreuve : le test sait-il détecter un partage ?**
On relance le même script en remplaçant les processus par des **threads** (`multiprocessing.dummy.Pool`,
même interface que `Pool`), qui, eux, partagent la mémoire du processus :

```
[ÉCHEC] Blocs traités hors du processus principal : PID des workers [21404], principal 21404
[ÉCHEC] LIGNES_VUES dans le processus principal = 100000 (attendu : 0, car chaque worker modifie sa propre copie)
```

Avec des threads, il n'y a qu'un seul PID, et la variable globale est partagée : elle atteint 100 000.
L'instruction `LIGNES_VUES += lignes` deviendrait alors une **vraie section critique**,
qu'il faudrait protéger par un `threading.Lock`.
Le test fait donc bien la différence : avec nos processus, il n'y a rien à protéger.

### 1.5 Conclusion P4

Il n'y a **aucune donnée partagée en écriture** entre workers. Il n'y a donc **aucune section critique**
et **aucun verrou à ajouter**. Ce n'est pas un oubli, c'est un **choix de conception** :

- **partitionner les données** : chaque worker a son bloc d'octets ;
- **calculer localement** : chaque worker a ses propres Counter ;
- **fusionner une seule fois à la fin**, dans un seul processus.

Ce choix est aussi plus rapide. Un verrou sur des Counter communs serait pris 9 millions de fois
(une fois par ligne), et les workers passeraient leur temps à s'attendre.

**Contre-exemple (ce qu'on n'a pas fait) :** si les workers ajoutaient chacun leurs comptes dans un même
`Manager().dict()`, l'instruction `total[ip] = total.get(ip, 0) + 1` serait une section critique.
Deux workers pourraient lire la même ancienne valeur et l'un des deux ajouts serait perdu.
Il faudrait l'entourer d'un `Lock` (`with verrou: ...`), réduit à cette seule ligne.

---

## 2. P5 — Absence d'interblocage

### 2.1 Critère du sujet

> Le rapport explique, à l'aide des conditions de Coffman, pourquoi votre programme ne peut pas se bloquer,
> avec le graphe ressources / processus.

Un **interblocage** (*deadlock*) se produit quand des processus s'attendent mutuellement, sans fin.
Exemple classique : P1 détient la ressource A et attend B, pendant que P2 détient B et attend A.

**Théorème de Coffman (1971) :** un interblocage n'est possible que si les **4 conditions** sont réunies
**en même temps**. Il suffit donc d'en casser **une seule** pour qu'il soit impossible.

### 2.2 Les ressources du programme

| Ressource | Utilisée par | Exclusive ? | Remarque |
| --- | --- | --- | --- |
| **R1 — Journal** `access.log` | tous les workers (et le principal dans `calculer_blocs()`) | Non | Lecture seule, chaque processus a son propre `open()`. Le principal **ferme** le fichier (`with`) **avant** de créer le `Pool`. |
| **R2 — File des tâches** du `Pool` | principal (dépose), workers (retirent) | Oui, un court instant | Verrou interne de `multiprocessing`, pris le temps de lire ou d'écrire **un** message. |
| **R3 — File des résultats** du `Pool` | workers (déposent), principal (retire) | Oui, un court instant | Idem. |
| **R4 — Processeurs (cœurs)** | tous | Oui, mais **réquisitionnables** | L'ordonnanceur du noyau retire le cœur à un processus quand il veut. |
| **R5 — Mémoire** | chacun la sienne | — | Espaces mémoire séparés (voir P4). |
| **R6 — stdout** | principal seul | — | Écrit une fois, après la fin des workers. |

### 2.3 Le graphe ressources / processus

Convention (graphe d'allocation de Holt) :

- **cercle `( )`** = processus ; **carré `[ ]`** = ressource ;
- `[R] ──► (P)` : R est **détenue** par P ;
- `(P) ──► [R]` : P **attend** R.

État le plus « chargé » possible : le principal attend les résultats, et un worker dépose le sien
pendant que les autres lisent leur bloc.

```
                   [ R1 journal ]   (lecture seule, partagée)
                  ╱       │       ╲
                 ▼        ▼        ▼
             ( W2 )    ( W3 )    ( WN )        lisent chacun leur bloc

   [ R3 file des résultats ] ──► ( W1 )        W1 détient un instant le verrou de R3
                ▲                              pour déposer son résultat, puis le relâche
                │
       ( P0 principal )                        P0 attend un message dans R3
                                               et ne détient aucune ressource exclusive
```

Le seul chemin d'attente est `P0 ──► R3 ──► W1`. Il s'arrête à W1, qui n'attend rien :
il finit de déposer son résultat et relâche R3. Aucune flèche ne revient vers P0, il n'y a donc **pas de cycle**.

Vu sous la forme plus simple du **graphe d'attente** (« qui attend qui ») :

```
                 ┌──► W1 ──► (n'attend personne : lit son bloc, puis dépose son résultat)
   P0 principal ─┼──► W2 ──► (n'attend personne)
                 ├──► W3 ──► (n'attend personne)
                 └──► WN ──► (n'attend personne)
```

Les flèches vont **toutes dans le même sens** : du principal vers les workers.
Aucun worker n'attend un autre worker (ils ne communiquent pas entre eux), et aucun worker n'attend le principal
pour terminer son bloc : il a reçu tout ce qu'il lui faut, `(chemin, debut, fin)`, dès le départ.
Le graphe est un **arbre**, il ne contient **aucun cycle**.

*Cas particulier :* un worker qui a **fini** son bloc attend dans R2 une nouvelle tâche, ou l'ordre de s'arrêter
envoyé à la sortie du `with Pool(...)`. C'est une flèche « worker ──► principal ». Elle ne ferme pas de cycle :
ce worker a **déjà rendu** son résultat, donc le principal ne l'attend plus. De plus, dans le principal, les tâches sont envoyées dans R2
par un thread interne du `Pool`, et les résultats sont lus par un autre : l'envoi des tâches ne dépend jamais de
l'arrivée des résultats.

### 2.4 Les 4 conditions de Coffman, une par une

| # | Condition | Présente chez nous ? | Pourquoi |
| --- | --- | --- | --- |
| 1 | **Exclusion mutuelle** : une ressource ne peut servir qu'à un processus à la fois | Presque pas | Le journal est lu en **partage** (lecture seule), la mémoire est séparée, stdout n'est utilisé que par le principal. Seuls les verrous internes des files du `Pool` (R2, R3) sont exclusifs, et pour un instant très court. |
| 2 | **Détention et attente** : un processus garde une ressource tout en en attendant une autre | **Non** | Un worker ne prend le verrou d'une file que pour lire ou déposer **un** message, puis le relâche : il ne demande jamais une 2e ressource en gardant la 1re. Le principal attend les résultats sans **rien détenir** qu'un worker demande (son fichier de `calculer_blocs()` est déjà fermé). |
| 3 | **Pas de réquisition** : on ne peut pas retirer une ressource à un processus | Partiellement | Les cœurs sont réquisitionnés par l'ordonnanceur du noyau. Les verrous internes du `Pool` ne le sont pas, mais cette condition seule ne suffit pas à bloquer. |
| 4 | **Attente circulaire** : P1 attend P2, qui attend … qui attend P1 | **Non** | Le graphe d'attente (2.3) va du principal vers les workers et s'arrête là : **aucun cycle** possible. |

**Conclusion :** les conditions **2 et 4 ne sont jamais réunies** (et la 1 presque pas).
Il en manque au moins une, donc, d'après Coffman, **notre programme ne peut pas se trouver en interblocage**.

Ce résultat découle directement de P4 : comme les workers ne partagent aucune donnée, ils n'ont aucun verrou à prendre,
donc rien à se disputer et rien à s'attendre.

### 2.5 Ce qui pourrait quand même faire « attendre sans fin » (à connaître pour la soutenance)

Ce ne sont **pas** des interblocages au sens de Coffman (aucun cycle d'attente), mais des cas où le programme
peut sembler figé :

1. **Oubli de `if __name__ == "__main__":`** — en mode `spawn` (macOS) ou `forkserver` (Linux, Python 3.14+),
   chaque worker réimporte le programme. Sans ce test, il relancerait lui-même l'analyse.
   Vécu pendant le développement : un test lancé depuis l'entrée standard est resté bloqué, car les workers ne pouvaient
   pas réimporter le script. Le test est présent dans `analyse_par.py` et dans `demontrer_p4.py`.
2. **Un worker tué par le système** (manque de mémoire, `kill -9`) — `Pool` remplace le processus, mais **la tâche
   en cours est perdue** et `starmap` attend un résultat qui n'arrivera jamais.
   Vérifié avec Python 3.15 sur le Mac (petit test séparé : une tâche se tue avec `SIGKILL`, `map_async(...).get(timeout=10)`
   est toujours en attente après 10 s).
   - *Prévention :* chaque worker lit par morceaux de 16 Mo (`TAILLE_LECTURE`), donc sa mémoire reste bornée, même avec 1 worker
     sur 1,9 Go : le risque de manque de mémoire est faible.
   - *Amélioration possible (non faite) :* `concurrent.futures.ProcessPoolExecutor`, qui lève `BrokenProcessPool`
     si un worker meurt, ou un `map_async(...).get(timeout=...)`.
