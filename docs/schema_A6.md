# ParaLog — Schéma en couches (A6)

Source pour le dossier d'architecture. Version dessinée pour le PDF : `docs/schema_A6.svg`.

Les appels système cités ici ont été **relevés réellement** avec `strace`, dans la VM Ubuntu (noyau Linux 7.2, Python 3.14), sur l'échantillon :

```bash
bash scripts/tracer_appels.sh                      # échantillon, 2 workers (Linux, strace requis)
bash scripts/tracer_appels.sh data/echantillon_access.log 4
```

## 1. Le schéma

Chaque couche ne parle qu'à la couche juste en dessous. Le programme Python ne touche jamais directement le disque ni le processeur : il passe par l'interpréteur, puis par la bibliothèque C, qui fait les **appels système**. Ce sont les seules portes d'entrée vers le noyau.

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ UTILISATEUR      membre du groupe paralog, dans un terminal                 │
 │                  $ bash scripts/lancer.sh data/echantillon_access.log 2     │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ SCRIPTS BASH     scripts/lancer.sh (interprété par /usr/bin/bash)           │
 │                  crée un processus fils, redirige > vers le rapport,        │
 │                  puis y lance python3        ── clone, openat + dup2, execve│
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ PROGRAMME        src/analyse_par.py + analyse_commun.py + rapport.py        │
 │                  open() / seek() / read() du journal, Pool(N), print()      │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ INTERPRÉTEUR     /usr/bin/python3 (CPython 3.14) : modules io,              │
 │ PYTHON           multiprocessing (forkserver, workers, threads du Pool)     │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ BIBLIOTHÈQUE C   glibc : fork(), open(), read()… traduits en appels système │
 ╞═════════════════════════ APPELS SYSTÈME (mode utilisateur → mode noyau) ════╡
 │   execve   clone / vfork   openat   lseek   read   write   dup2             │
 ╞═════════════════════════════════════════════════════════════════════════════╡
 │ NOYAU LINUX      gestion des processus et ordonnanceur (qui tourne sur      │
 │                  quel cœur), système de fichiers et cache disque,           │
 │                  contrôle des droits (A3), mémoire de chaque processus      │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ MATÉRIEL         Intel Core i5-8210Y (2 cœurs physiques, 4 threads),        │
 │                  mémoire vive, disque SSD                                   │
 └─────────────────────────────────────────────────────────────────────────────┘
```

**Mode utilisateur / mode noyau :** tout ce qui est au-dessus de la double ligne s'exécute en mode utilisateur, sans accès direct au matériel. Pour lire un fichier ou créer un processus, un programme doit **demander au noyau** par un appel système. Le processeur passe alors en mode noyau, le noyau vérifie la demande (droits, paramètres), la réalise, puis rend la main.

## 2. Ce que montre la trace d'un lancement (N = 2)

Extrait réel de `bash scripts/tracer_appels.sh` (les PID changent à chaque lancement) :

```
PID 1229 — bash : scripts/lancer.sh
    execve("/usr/bin/bash", ["bash", "scripts/lancer.sh", "data/echantillon_access.log", "2"], ... = 0
    clone(flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, ...) = 1234
PID 1234 — python3 : programme principal
    openat(AT_FDCWD, "resultats/rapport_20261027_110653_echantillon_access_N2.txt", O_WRONLY|O ... = 3
    dup2(3, 1)                              = 1
    execve("/usr/bin/python3", ["python3", "src/analyse_par.py", "data/echantillon_access.log" ... = 0
    openat(AT_FDCWD, "data/echantillon_access.log", O_RDONLY|O_CLOEXEC) = 3
    lseek(3, 10297143, SEEK_SET)            = 10297143
    read(journal) x 1 : 131072 octets lus au total
    vfork()                                 = 1236
    write(1, "=== Rapport ParaLog ===\nJournal analys\303\251 : data/echantillon_access.log\nL ... = 1318
    clone3(CLONE_VM|CLONE_THREAD...) x 3 : threads, mémoire partagée
PID 1236 — forkserver de Python (crée les workers)
    execve("/usr/bin/python3", ["/usr/bin/python3", "-c", "import sys; from multiprocessing.fo ... = 0
    clone(flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, ...) = 1237
    clone(flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, ...) = 1238
PID 1237 — worker (créé par clone, sans execve)
    openat(AT_FDCWD, "data/echantillon_access.log", O_RDONLY|O_CLOEXEC) = 6
    lseek(6, 0, SEEK_SET)                   = 0
    read(journal) x 2 : 10354688 octets lus au total
PID 1238 — worker (créé par clone, sans execve)
    openat(AT_FDCWD, "data/echantillon_access.log", O_RDONLY|O_CLOEXEC) = 6
    lseek(6, 10297292, SEEK_SET)            = 10297292
    read(journal) x 2 : 10296994 octets lus au total
```

Le PID 1234 est d'abord un **fils de bash** : il ouvre le rapport et fait `dup2` (c'est la redirection `>`), puis `execve` le transforme en python3, sans changer de PID. C'est pour ça que ces deux lignes apparaissent avant l'`execve`.

L'arbre des processus qui en découle :

```
bash lancer.sh (1229)
 ├── dirname, date, basename, tail      (clone puis execve : commandes du script)
 └── python3 analyse_par.py (1234)      (clone, redirection > , puis execve)
      ├── 3 threads du Pool             (clone3 avec CLONE_THREAD : même mémoire)
      ├── resource_tracker (1235)       (vfork + execve, outil interne de Python)
      └── forkserver (1236)             (vfork + execve)
           ├── worker 1 (1237)          (clone : bloc 0 → 10 297 292)
           └── worker 2 (1238)          (clone : bloc 10 297 292 → fin)
```

## 3. Les appels système utilisés

| Appel système | Catégorie | Qui l'appelle, et où dans notre code | Ce que fait le noyau |
| --- | --- | --- | --- |
| `clone` | Création de processus | bash, pour chaque commande du script ; le **forkserver**, pour chaque worker de `Pool(processes=n)` (`analyse_par.py`, `main()`) | Crée un nouveau processus, copie de son parent, avec un nouveau PID et **sa propre mémoire** |
| `vfork` | Création de processus | Python, pour démarrer le forkserver (suivi aussitôt d'un `execve`) | Comme `clone`, mais le parent attend l'`execve` du fils : plus rapide quand on remplace tout de suite le programme |
| `execve` | Lancement d'un programme | bash, pour lancer `python3 src/analyse_par.py` (`lancer.sh`) | Remplace le programme du processus (ici bash) par un autre (python3), **en gardant le même PID** |
| `openat` | Lecture de fichier | Chaque worker : `open(chemin, "rb")` (`lire_lignes()`) ; le principal : `calculer_blocs()` | Vérifie les **droits** (tableau A3), puis renvoie un descripteur (un petit entier, ici 3 ou 6) |
| `lseek` | Lecture de fichier | `fichier.seek(debut)` : chaque worker se place au début de son bloc | Déplace la position de lecture du descripteur, sans rien lire |
| `read` | Lecture de fichier | `fichier.read(...)` et `readline()` | Copie les octets du disque (ou du cache disque) vers la mémoire du processus |
| `dup2` | Redirection | bash, pour `> "$RAPPORT"` (`lancer.sh`) | Fait pointer la sortie standard (descripteur 1) vers le fichier du rapport |
| `write` | Écriture de fichier | `print()` du rapport dans `main()` | Écrit 1 318 octets sur le descripteur 1, c'est-à-dire dans le rapport |

Le sujet demande au moins deux appels système (lecture de fichier, création de processus) : on en montre **huit**, dont `openat` + `lseek` + `read` pour la lecture, et `clone` (+ `vfork`, `execve`) pour la création de processus.

## 4. Ce qu'il faut retenir

- **Créer un processus et lancer un programme sont deux étapes :** `clone` crée une copie du processus, puis `execve` remplace le programme de cette copie. bash fait les deux pour lancer python3. Les workers, eux, ne font **que** `clone` : ce sont des copies du forkserver, qui contient déjà Python et notre code.
- **Processus ou thread, c'est le même appel :** `clone` sans `CLONE_VM` crée un processus (mémoire séparée : les workers) ; `clone3` avec `CLONE_VM|CLONE_THREAD` crée un thread (mémoire partagée : les 3 threads internes du `Pool`). Le noyau montre ainsi que nos workers **ne partagent pas de mémoire** (P4).
- **Chaque worker ouvre lui-même le journal :** deux `openat` distincts, donc deux descripteurs, chacun avec sa propre position de lecture. Le `lseek` d'un worker ne gêne pas l'autre (P4).
- **Le découpage se voit dans la trace :** le principal se place au milieu du fichier (`lseek(3, 10297143)`) puis lit un morceau pour trouver la fin de la ligne : le worker 2 commence à 10 297 292, juste après ce saut de ligne. Le worker 2 lit exactement 20 594 286 − 10 297 292 = 10 296 994 octets, jusqu'à la fin du fichier.
- **La lecture se fait par gros morceaux :** chaque worker lit son bloc de 10 Mo en 2 `read`, et non ligne par ligne. Un appel système coûte cher (passage en mode noyau) : moins d'appels, c'est plus rapide.
- **Le worker 1 lit 57 396 octets de plus que son bloc :** Python lit par multiples de son tampon de 128 Kio (131 072 octets). Le 1er `read` demande 10 223 616 octets (78 × 131 072), puis la fin du bloc est lue avec un tampon complet de 128 Kio, qui déborde sur le bloc suivant. Ces octets sont lus par le noyau mais jamais analysés : `fichier.read()` ne rend à `lire_lignes()` que les octets du bloc, le surplus reste dans le tampon de Python.
- **Les droits A3 sont vérifiés par le noyau, au moment de `openat` :** vérifié dans la VM sur un fichier en 640 dans un dossier en 750 (groupe `paralog`) :

  ```
  exterieur  : openat(AT_FDCWD, ".../data/j.log", O_RDONLY|O_CLOEXEC) = -1 EACCES (Permission denied)
  coequipier : openat(AT_FDCWD, ".../data/j.log", O_RDONLY|O_CLOEXEC) = 3
  ```

  Python transforme cette erreur en `PermissionError`, que nos programmes attrapent (`OSError`) : message « impossible de lire », code 1.
- **Le noyau répartit les processus sur les cœurs :** c'est l'ordonnanceur qui place les workers sur les cœurs physiques ; d'où la meilleure accélération avec 2 workers sur ce processeur à 2 cœurs physiques (P6, P7).

## 5. Limites

- `strace` n'existe que sous Linux (sous macOS, l'équivalent `dtruss` demande de désactiver une protection du système). Le relevé se fait donc dans la VM Ubuntu.
- `strace` ralentit fortement le programme (chaque appel système est intercepté) : les temps affichés pendant le relevé ne sont pas des mesures de performance.
- Avec Python 3.14 sous Linux, les workers sont créés par un processus intermédiaire, le **forkserver**. Avec Python 3.8 à 3.13, c'est le processus principal qui ferait directement `clone` (méthode `fork`). L'appel système reste le même.
