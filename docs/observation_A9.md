# ParaLog — Observation du système (A9)

Ce document fait partie du dossier d'architecture. Il présente un relevé des processus pris **pendant** une
exécution de la version parallèle, et le commente. Il répond au critère A9 du sujet (Bonus).

## 1. Critère du sujet et méthode

> Pendant une exécution, vous relevez les processus créés (PID, état, cœur utilisé) avec `ps`, `top` ou `htop`,
> et vous commentez ce relevé dans le dossier.

### 1.1 Le script : `scripts/observer.sh`

```bash
bash scripts/observer.sh data/access.log 4      # -> resultats/observation_access_N4.txt
bash scripts/observer.sh data/echantillon_access.log 4 0.01   # essai rapide (l'analyse dure < 0,1 s)
```

- Lance `python3 src/analyse_par.py JOURNAL N` **en arrière-plan** (`&`), puis, tant qu'il existe (`kill -0`),
  prend une « photo » avec `ps` toutes les 0,2 s (3e argument facultatif).
- Une photo = le processus principal **et tous ses descendants** : `ps -e` liste tous les processus, puis `awk`
  garde le principal, ajoute ceux dont le parent (PPID) est déjà gardé, et recommence jusqu'à ce qu'il n'y en ait
  plus de nouveaux. Un rôle est donné à chacun : principal, `forkserver`, `resource_tracker` ou worker.
- Colonnes demandées à `ps` : `pid, ppid, stat` (état), `psr` (**cœur utilisé**), `pcpu`, `nlwp` (nombre de threads).
- À la fin, un résumé donne, pour chaque processus, les états et les cœurs vus sur l'ensemble des photos.
- Linux uniquement : la colonne `psr` n'existe pas dans le `ps` de macOS. Codes : 0 = OK ; 1 = fichier absent ou
  illisible, `ps` sans `psr`, analyse en échec ; 2 = mauvaise utilisation (arguments, N, intervalle).

**Pourquoi `ps` plutôt que `top` :** `ps` donne directement les trois informations demandées (PID, état, cœur),
une ligne par processus, facile à filtrer avec `awk` et à enregistrer dans un fichier. `top` est interactif ;
`htop` n'est pas installé.

**Machine du relevé :** PC portable, Intel Core Ultra 9 185H, Windows avec WSL2, Python 3.12.3, 28/10/2026.
Linux y voit **11 cœurs physiques × 2 = 22 cœurs logiques** (numérotés 0 à 21) ; les cœurs logiques `2k` et
`2k+1` sont sur le même cœur physique `k` (`lscpu -p=CPU,Core`). C'est la topologie présentée par l'hyperviseur
de WSL : la vraie puce mélange des cœurs « performance » (avec hyperthreading) et « efficaces » (sans).
Ce n'est ni le Mac de P6 / P7, ni le PC de P8.

## 2. Le relevé (`resultats/observation_access_N4.txt`, extraits)

`access.log` (9 M lignes), **4 workers**, 24 photos, temps d'analyse **4,96 s**.

```
  RÔLE                PID    PPID  STAT  PSR  %CPU NLWP
--- photo 1, t = 0.00 s
  principal          18685   18677  R+     10   0.0    1
--- photo 2, t = 0.21 s
  principal          18685   18677  Sl+    11  13.6    4
  worker             18692   18685  R+      8  89.4    1
  worker             18693   18685  R+      2  89.4    1
  worker             18694   18685  R+      6  89.4    1
  worker             18695   18685  R+     20  89.4    1
  ...
--- photo 13, t = 2.54 s
  principal          18685   18677  Sl+    11   1.1    4
  worker             18692   18685  D+      9  97.6    1
  worker             18693   18685  R+      2  97.6    1
  worker             18694   18685  R+      7  97.6    1
  worker             18695   18685  R+     20  97.2    1
  ...
--- photo 24, t = 4.87 s
  principal          18685   18677  Sl+    11   0.6    4
  worker             18692   18685  S+      9  97.7    1
  worker             18693   18685  S+      3  98.1    1
  worker             18694   18685  R+      7  98.3    1
  worker             18695   18685  R+     21  98.1    1

=== Résumé par processus (états et cœurs vus sur l'ensemble des photos) ===
  RÔLE                 PID  PHOTOS  ÉTATS    CŒURS
  principal          18685      24  R S      10 11
  worker             18692      23  R D S    8 9
  worker             18693      23  R S      2 3
  worker             18694      23  R        6 7
  worker             18695      23  R        20 21
```

Lecture de `STAT` : `R` = en cours d'exécution (ou prêt) ; `S` = endormi, en attente d'un événement ;
`D` = attente non interruptible (en général une entrée / sortie disque) ; `l` = plusieurs threads ;
`+` = groupe de processus au premier plan du terminal.

## 3. Commentaire

### 3.1 Les processus créés : 1 principal + 4 workers

- Les 4 workers ont pour parent (`PPID`) le principal 18685, qui a lui-même pour parent le bash d'`observer.sh`
  (18677). Ce sont bien des **processus** distincts, avec leurs propres PID : c'est la base de P4 (mémoire séparée).
- Avec Python 3.12 sous Linux, `multiprocessing` crée les workers par **`fork`** : copies directes du principal.
  À partir de Python 3.14, la méthode par défaut est **`forkserver`** : on verrait en plus un processus
  `forkserver` (parent des workers) et un `resource_tracker`. Vérifié sur une copie du dépôt en forçant
  `set_start_method("forkserver")` : le script reconnaît bien ces deux rôles. (Même arbre que la trace `strace` de A6.)
- **Photo 1** : le principal est seul, avec 1 thread, en train de calculer les blocs (`calculer_blocs`) avant de
  créer le `Pool`. Moins de 0,2 s plus tard, les 4 workers existent déjà : la création des processus est rapide (P7).

### 3.2 Les états : les workers calculent, le principal attend

- **Workers en `R` sur presque toutes les photos, `%CPU` de 89 à 98 %** : chaque worker occupe un cœur entier.
  Le travail est du **calcul** (découpage des lignes, `Counter`), pas de l'attente.
- **Principal en `Sl`** (endormi, plusieurs threads) dès la photo 2, avec un `%CPU` qui tend vers 0 : il ne fait
  rien pendant l'analyse, il attend les résultats dans `pool.starmap()`. Il ne lit pas le fichier et ne touche à
  aucune donnée des workers : c'est ce qu'affirme P4, vu ici depuis le système.
- **`NLWP` = 4 pour le principal** : son thread principal + les **3 threads internes du `Pool`** (gestion des
  workers, envoi des tâches, réception des résultats). Ce sont les 3 `clone3(CLONE_THREAD)` relevés en A6.
  Chaque worker n'a qu'**1** thread.
- **Un seul `D`** (worker 18692, photo 13) : attente d'une lecture disque, sans doute un morceau de 16 Mo qui
  n'était pas encore dans le cache. Une photo sur 92 photos de workers : le fichier était presque entièrement
  en mémoire cache (lancements précédents), la lecture ne freine presque pas. Une seule observation : c'est une
  explication probable, pas une mesure.
- **Photo 24** : deux workers passent en `S` : ils ont fini leur bloc et attendent (résultat renvoyé, plus de
  tâche). Les 4 finissent presque en même temps, ce qui montre que les blocs, de même taille en octets, sont
  **équilibrés**.
- **`%CPU` est une moyenne** sur toute la vie du processus (temps CPU ÷ temps écoulé), pas une valeur
  instantanée : c'est pour ça qu'il monte doucement (89 → 98 %) au lieu d'être à 100 % tout de suite.

### 3.3 Les cœurs utilisés : 4 workers, 4 cœurs physiques différents

- À chaque photo, les 4 workers sont sur **4 cœurs différents** : ils calculent **vraiment en même temps**.
  C'est l'inverse des threads de P8 (un seul thread exécute du Python à la fois, à cause du GIL).
- Les cœurs logiques utilisés (8 ou 9, 2 ou 3, 6 ou 7, 20 ou 21) sont sur **4 cœurs physiques différents**
  (4, 1, 3 et 10) : aucun worker ne partage les unités de calcul d'un autre (pas de conflit d'hyperthreading,
  contrairement au Mac à N = 4 en P7).
- **Changements de cœur** : chaque worker change de cœur au plus une fois, et toujours vers le cœur logique
  **voisin du même cœur physique** (8 → 9, 2 → 3, 6 → 7, 20 → 21 ; principal 10 → 11). L'ordonnanceur de Linux
  déplace un processus quand il le juge utile, mais préfère le garder près de son cœur : les données déjà dans le
  cache du cœur physique restent utilisables.
- Le choix des cœurs est fait par le **noyau**, pas par notre programme (on ne fixe aucune affinité).

### 3.4 Limites du relevé

- Une photo toutes les 0,2 s : ce qui se passe entre deux photos n'est pas vu (un état `D` très court peut être
  manqué, par exemple).
- `ps` lui-même consomme un peu de CPU, sur un cœur que les 4 workers n'utilisent pas (22 cœurs logiques).
- Une seule exécution, sur une machine virtuelle (WSL) : les numéros de cœurs sont ceux que voit Linux.
