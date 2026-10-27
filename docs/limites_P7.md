# ParaLog — Analyse des limites (P7)

Ce document fait partie du rapport de performance. Il explique pourquoi l'accélération de la version
parallèle `src/analyse_par.py` (P2) n'est pas proportionnelle au nombre de workers, et répond au critère P7 du sujet.

## 1. Critère du sujet et mesures utilisées

> Vous expliquez pourquoi le gain n'est pas proportionnel au nombre de workers : nombre de cœurs,
> coût de création des processus, lecture du disque, partie non parallélisable.

### 1.1 Le constat (mesures P6)

Mesures officielles de P6 (`resultats/mesures_p2_access.txt`, 3 essais, médianes, fichier complet de 9 000 000 lignes) :

| Version | Médiane | Accélération mesurée | Accélération idéale |
| --- | --- | --- | --- |
| Séquentiel (P1) | 34,534 s | x1,00 | x1 |
| P2, 1 worker | 38,239 s | x0,90 | x1 |
| P2, 2 workers | 23,962 s | **x1,44** | x2 |
| P2, 4 workers | 27,949 s | x1,24 | x4 |
| P2, 8 workers | 30,136 s | x1,15 | x8 |

Accélération = temps séquentiel ÷ temps parallèle. Le graphique `resultats/graphique_p2_access.svg` montre
l'écart entre la courbe mesurée et la droite idéale (accélération = N).

**Machine :** MacBook Air, Intel Core i5-8210Y @ 1,60 GHz (série « Y », basse consommation, 7 W, sans ventilateur),
**2 cœurs physiques, 4 cœurs logiques** (hyperthreading), 8 Go de RAM, macOS, Python 3.15.0.
Le dépôt est rangé dans le dossier partagé d'OrbStack, monté en **NFS** (partage réseau local) sur le Mac.

### 1.2 La décomposition du temps : `scripts/mesurer_limites.py`

Pour ne pas s'appuyer sur des hypothèses, chaque cause a été **mesurée** par un script qui appelle
les vraies fonctions de P2 sans les modifier :

```bash
python3 scripts/mesurer_limites.py data/access.log > resultats/limites_access.txt
```

| Mesure | Ce qu'elle isole |
| --- | --- |
| Lecture seule du fichier, puis lecture + décodage en lignes (sans analyse) | Le coût du **disque** |
| « Pool vide » : créer N workers, leur donner une tâche vide, les arrêter | Le coût de **création des processus** |
| Pour chaque worker : temps écoulé (`time.perf_counter()`) et temps de calcul (`time.process_time()`) | Le **nombre de cœurs** : un worker qui attend un cœur libre a un temps écoulé plus grand que son temps de calcul |
| Découpage, surcoût du Pool (phase parallèle − worker le plus long), fusion, taille des résultats renvoyés | La **partie non parallélisable** |

Résultat sur `access.log` (Mac, 27/10/2026, une exécution) :

| N | Pool vide | Découpage | Phase parallèle | Worker le plus long | Surcoût du Pool | Fusion | Total | CPU total des workers | Résultats renvoyés | Part non parallèle |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0,450 s | 0,002 s | 36,814 s | 36,657 s | 0,158 s | 0,000 s | 36,817 s | 33,254 s | 116 ko | 0,4 % |
| 2 | 0,251 s | 0,003 s | 21,242 s | 21,079 s | 0,163 s | 0,002 s | 21,247 s | 40,320 s | 228 ko | 0,8 % |
| 4 | 0,363 s | 0,003 s | 34,255 s | 33,976 s | 0,279 s | 0,007 s | 34,265 s | 82,925 s | 448 ko | 0,8 % |
| 8 | 0,526 s | 0,008 s | 29,494 s | 28,863 s | 0,630 s | 0,016 s | 29,518 s | 84,974 s | 887 ko | 2,2 % |

Temps d'un worker (écoulé / calcul) :

| N | Chaque worker | Part du temps passée à calculer |
| --- | --- | --- |
| 1 | 36,66 s / 33,25 s | 91 % |
| 2 | ≈ 21,0 s / 20,2 s | 96 % |
| 4 | ≈ 33,9 s / 20,7 s | 61 % |
| 8 | ≈ 28,5 s / 10,6 s | 37 % |

Lecture du disque (processus principal) : lecture seule **26,611 s (70 Mo/s)**, puis lecture + décodage + découpage en lignes **16,920 s**.

**Attention :** c'est une seule exécution. Le processeur change de fréquence selon sa température, donc les temps
varient d'un essai à l'autre (ici N = 4 est plus lent que N = 8, l'inverse des médianes de P6).
Les accélérations de référence restent celles de P6 ; cette décomposition sert à les **expliquer**.

---

## 2. Cause 1 — Le nombre de cœurs (cause principale)

**Idée :** des processus ne vont plus vite que s'il y a des cœurs libres pour les exécuter **en même temps**.
Notre machine n'a que **2 cœurs physiques**.

- **N = 2, un worker par cœur physique :** chaque worker calcule 96 % du temps (21,0 s écoulées pour 20,2 s de calcul).
  Les deux cœurs travaillent vraiment en parallèle : c'est la meilleure configuration (x1,44 en P6).
- **N = 4, les cœurs logiques de l'hyperthreading :** un cœur physique exécute deux fils d'instructions, mais ils se
  partagent les mêmes unités de calcul. Le **CPU total double** (40,3 s → 82,9 s) pour **le même travail** :
  chaque worker a « un cœur » à lui, mais un demi-cœur de puissance. On ne calcule pas plus vite, et il y a plus de
  processus à créer et de résultats à fusionner.
- **N = 8, plus de workers que de cœurs logiques :** chaque worker ne calcule que 37 % du temps (10,6 s sur 28,5 s) :
  le reste, il **attend son tour**. L'ordonnanceur du noyau fait tourner 8 processus sur 4 cœurs logiques
  (changements de contexte). Le CPU total (85,0 s) est le même qu'avec N = 4 : la machine est déjà saturée.

**Effet de la fréquence (Turbo Boost).** Entre 1 et 2 workers, le CPU total passe de 33,3 s à 40,3 s
(**+21 %**) pour le même travail. Avec un seul cœur actif, ce processeur monte en fréquence (Turbo Boost,
jusqu'à 3,6 GHz d'après la fiche Intel) ; avec deux cœurs actifs, il est limité par sa puissance (7 W) et par sa
température (pas de ventilateur), donc chaque cœur va moins vite.
Accélération attendue avec 2 cœurs, en tenant compte de cette baisse : 2 ÷ 1,21 ≈ **x1,65**.
Mesuré entre 1 et 2 workers : **x1,60** en P6 (38,239 ÷ 23,962) et x1,73 ici. **L'essentiel de l'écart à x2 vient de là.**

**Conclusion :** au-delà de 2 workers, il n'y a plus de cœur physique libre ; ajouter des workers ajoute du coût sans ajouter de calcul.

---

## 3. Cause 2 — Le coût de création des processus

Avant d'analyser, il faut **créer** les workers. Sur macOS, `multiprocessing` utilise la méthode `spawn` :
chaque worker est un **nouvel interpréteur Python** qui démarre, réimporte `analyse_par.py`, `analyse_commun.py` et `rapport.py`,
puis attend ses tâches. À la fin, les workers sont arrêtés.

- Pool vide : **0,25 s à 0,53 s**, et le coût augmente avec N (0,25 s pour 2 workers, 0,53 s pour 8).
- Surcoût réel de la phase parallèle (démarrage, envoi des tâches, renvoi des résultats, arrêt) : **0,16 s à 0,63 s**.

**Sur le fichier complet, ce coût est faible** (moins de 2 % du total). **Sur l'échantillon** (100 000 lignes,
analyse d'environ 0,3 s), il est du même ordre que l'analyse elle-même : la part non parallèle va de 26 % (N = 1)
à 68 % (N = 8), et P2 est **plus lent** que P1. Paralléliser n'est rentable que si le travail est assez gros.

**1 worker plus lent que P1 (x0,90) :** c'est le même travail qu'en P1, plus le coût du parallélisme
(créer un processus, renvoyer les résultats). Le coût mesuré (environ 0,5 s) n'explique qu'une partie des 3,7 s d'écart
entre les médianes ; le reste est dans la dispersion des mesures (les 3 essais à 1 worker vont de 35,5 s à 39,7 s).

---

## 4. Cause 3 — La lecture du disque

Le journal fait 1,86 Go. Avant d'être analysé, il doit être **lu** : c'est une ressource **unique**,
partagée par tous les workers. Ajouter des workers ajoute du calcul, pas de vitesse de lecture.

- **Lecture à froid : 26,6 s (70 Mo/s)**, presque autant que toute l'analyse avec 2 workers (21,2 s).
  Le dépôt est sur le partage NFS d'OrbStack : chaque lecture passe par ce partage réseau local.
  Si le fichier n'est pas déjà en mémoire, **quel que soit N, l'analyse ne peut pas descendre sous ~26 s** :
  c'est le temps qu'il faut pour faire arriver les octets.
- **En cache :** le système garde le fichier lu en mémoire (8 Go de RAM pour 1,86 Go de fichier) ; les lectures
  suivantes sont bien plus rapides (468 Mo/s mesurés sur l'échantillon). C'est pourquoi, en P6, le **1er essai** de chaque
  version est souvent plus lent (P1 : 40,9 s puis 34,3 s et 34,5 s ; 2 workers : 27,4 s puis 23,6 s et 24,0 s).
  `mesurer.sh` entrelace les essais et prend la médiane pour limiter cet effet.
- **Même en cache, la lecture coûte :** avec 1 worker, 36,7 s écoulées pour 33,3 s de calcul, soit **3,4 s d'attente**
  (lecture des morceaux de 16 Mo).
- **Hypothèse probable (non mesurée) :** le serveur NFS d'OrbStack consomme lui-même du temps processeur. Avec 4 workers
  sur 4 cœurs logiques, il entre en concurrence avec eux, ce qui expliquerait les 13 s par worker passées sans calculer à N = 4.

**Où part le temps de calcul :** lecture + décodage + découpage en lignes prennent 16,9 s, soit environ la **moitié**
du travail d'un worker seul (33,3 s de calcul) ; l'autre moitié est l'analyse des lignes (`analyser_ligne()` et les Counter).
Ces deux parties sont faites **dans les workers**, donc elles sont bien parallélisées.

---

## 5. Cause 4 — La partie non parallélisable (loi d'Amdahl)

**Loi d'Amdahl :** si une fraction `f` du travail est séquentielle, l'accélération maximale avec N cœurs est

```
S(N) = 1 / ( f + (1 - f) / N )
```

Même avec une infinité de cœurs, on ne dépasse pas `1 / f`.

**Ce qui est séquentiel dans notre programme** (fait par le seul processus principal) :

| Partie | Temps mesuré (N = 1 à 8) |
| --- | --- |
| Découpage en blocs (`calculer_blocs()`, quelques `seek` + `readline`) | 2 à 8 ms |
| Surcoût du Pool : démarrage des workers, envoi des tâches, renvoi des résultats (pickle), arrêt | 0,16 à 0,63 s |
| Fusion des Counter (`fusionner()`) | 0 à 16 ms |
| **Total, en part du temps** | **0,4 % à 2,2 %** |

Avec `f = 2,2 %`, Amdahl autorise jusqu'à **x6,9 avec 8 vrais cœurs** (et x1,98 avec 2).
Notre partie non parallélisable est donc **trop petite pour expliquer** le x1,15 mesuré avec 8 workers :
la limite vient du **matériel** (2 cœurs physiques, baisse de fréquence, lecture du disque), pas du programme.

**Elle grandit avec N :** les résultats renvoyés passent de 116 ko (N = 1) à 887 ko (N = 8), car chaque worker renvoie
ses propres Counter (les mêmes IP et pages apparaissent dans tous les blocs), et la fusion porte sur N résultats.
Sur une machine avec beaucoup de cœurs, cette partie finirait par compter.

---

## 6. Synthèse

| Cause (sujet) | Preuve mesurée | Poids sur notre machine |
| --- | --- | --- |
| Nombre de cœurs | CPU total ×2 de N = 2 à N = 4 (hyperthreading) ; workers à 37 % de calcul à N = 8 ; +21 % de CPU de N = 1 à N = 2 (fréquence) | **Principal** : plafond à 2 cœurs physiques |
| Coût de création des processus | Pool vide 0,25–0,53 s ; surcoût 0,16–0,63 s | Faible sur le fichier complet, dominant sur l'échantillon |
| Lecture du disque | 26,6 s à froid (70 Mo/s, partage NFS) ; 3,4 s d'attente même en cache | Fort à froid, faible en cache |
| Partie non parallélisable | Découpage + surcoût + fusion = 0,4 à 2,2 % | Faible, mais augmente avec N |

**En une phrase :** le meilleur N est **le nombre de cœurs physiques** (2 ici). Au-delà, les workers en plus
se partagent les mêmes unités de calcul et coûtent plus qu'ils ne rapportent.

---

## 7. Limites de cette analyse

- **Une seule exécution** de `mesurer_limites.py` : les tendances sont nettes, mais les temps exacts varient d'un essai à l'autre.
- **Mesure faite sur le Mac** (comme P6), avec le dépôt sur le partage NFS d'OrbStack. Sur un disque local ou un vrai serveur
  Linux, la lecture serait plus rapide et l'accélération probablement meilleure.
- **Ordre des mesures :** la lecture seule passe en premier et met le fichier en cache pour les mesures suivantes.
- **Améliorations possibles (non faites) :** placer le journal sur un disque local ; régler N sur le nombre de **cœurs physiques**
  plutôt que sur `os.cpu_count()` (qui compte les cœurs logiques) ; mesurer sur une machine avec plus de cœurs.
