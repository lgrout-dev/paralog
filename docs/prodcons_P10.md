# ParaLog — Variante producteur / consommateur (P10)

Ce document fait partie du rapport de performance. Il présente une variante de P2 où un seul **producteur**
lit le fichier et remplit une **file bornée**, vidée par N **consommateurs**, et compare ses temps à ceux de P2.
Il répond au critère P10 du sujet (Bonus).

## 1. Critère du sujet et méthode

> Une variante où un producteur lit le fichier et alimente une file bornée, consommée par N workers.
> Vous comparez ses temps à ceux de P2.

### 1.1 Le programme : `src/analyse_prodcons.py`

```
                                          ┌─► consommateur 1 ─┐
producteur (processus principal)          ├─► consommateur 2 ─┤
  lit le fichier par lots de 1 Mo  ──►  file bornée  ──►  ...  ├──► fusionner() ──► rapport
  (recalés sur les "\n")              (2 × N lots max) └─► consommateur N ─┘
```

| | P2 (`analyse_par.py`) | P10 (`analyse_prodcons.py`) |
| --- | --- | --- |
| Qui lit le fichier ? | **chaque worker**, son bloc (`seek` + `read`) | **le producteur seul**, tout le fichier |
| Répartition du travail | fixée au départ : N blocs de même taille | au fil de l'eau : un consommateur libre prend le lot suivant |
| Données envoyées entre processus | 3 nombres par worker `(chemin, debut, fin)` | **tout le fichier** (1,86 Go), lot par lot, dans un tube |
| Donnée partagée | aucune (P4) | **la file** |

- **File bornée :** `multiprocessing.Queue(maxsize=2 * n)`. `put()` attend tant que la file contient 2N lots :
  le producteur n'a jamais plus de 2N Mo d'avance, la mémoire reste bornée quelle que soit la taille du journal.
  `get()` attend tant que la file est vide.
- **Lots en octets :** le producteur lit 1 Mo, le prolonge jusqu'au `\n` suivant (`readline()`) et l'envoie tel
  quel. Le consommateur décode et découpe (`errors="replace"`, `split("\n")`, comme P2), puis appelle
  `analyser_lignes()`, **la même fonction qu'en P1 / P2**. Envoyer un `bytes` est le transfert le moins cher
  (une copie) ; des listes de 10 000 chaînes coûteraient beaucoup plus à sérialiser.
- **Fin :** le producteur dépose un marqueur `None` par consommateur ; chacun s'arrête en le recevant et
  renvoie **un** résultat dans une seconde file. Le principal lit les N résultats **puis** fait `join()` (voir §5).
- Même interface, mêmes messages, mêmes codes de retour et même chronomètre que P2. `lire_nombre_workers`
  est importé de P2.

**Vérifié sur l'échantillon :** rapport identique à P1 pour N = 1, 2, 4, 8 ; aussi avec des lots forcés à
1 000 octets (≈ 20 000 lots, beaucoup de lignes coupées), sur un fichier vide, sur un fichier de 11 lignes
(6 mal formées, un octet invalide, dernière ligne sans `\n`) et en mode `forkserver` (Python ≥ 3.14).

### 1.2 Le script de mesure : `scripts/mesurer_p10.sh`

```bash
bash scripts/mesurer_p10.sh data/access.log      # -> resultats/mesures_p10_access_linux.txt et .csv
```

Même méthode que P8 (`mesurer_p8.sh`) : séquentiel, P2 et P10 pour N = 1, 2, 4, 8, **3 essais entrelacés**,
médiane, accélération, temps CPU (user + sys) et **cœurs occupés = CPU ÷ temps réel** ; chaque rapport est comparé
au séquentiel (`diff`). En plus : le rapport **P10 ÷ P2 à N égal**.

**Machine :** PC portable, Intel Core Ultra 9 185H, Windows avec WSL2 (Linux voit 11 cœurs physiques,
22 logiques), Python 3.12.3, 28/10/2026. Ce n'est ni le Mac de P6 / P7 ni le PC de P8 : les chiffres ci-dessous
se comparent entre eux. P2 est mesuré **dans la même session** que P10, pour une comparaison honnête.

## 2. Résultats (`resultats/mesures_p10_access_linux.txt`, médianes de 3 essais)

`access.log`, 9 000 000 lignes. Les 27 rapports sont identiques au séquentiel.

| N | P2 : temps | P2 : accél. | P10 : temps | P10 : accél. | **P10 ÷ P2** | Cœurs occupés P2 / P10 |
| --- | --- | --- | --- | --- | --- | --- |
| séquentiel | 14,208 s | x1,00 | | | | 1,00 |
| 1 | 14,975 s | x0,95 | 17,205 s | x0,83 | **x1,15** | 1,00 / 1,05 |
| 2 | 7,721 s | x1,84 | 8,826 s | x1,61 | **x1,14** | 1,96 / 2,07 |
| 4 | 4,210 s | x3,37 | 4,715 s | x3,01 | **x1,12** | 3,89 / 4,01 |
| 8 | 2,862 s | **x4,96** | 3,275 s | **x4,34** | **x1,14** | 7,21 / 6,82 |

Temps CPU (médianes, en secondes) :

| N | P2 user | P2 sys | P10 user | P10 sys |
| --- | --- | --- | --- | --- |
| 1 | 14,49 | 0,53 | 14,94 | **3,21** |
| 2 | 14,58 | 0,75 | 15,71 | **2,77** |
| 4 | 15,13 | 1,09 | 16,12 | **3,10** |
| 8 | 19,47 | 2,03 | 19,26 | **3,18** |

**En résumé : P10 accélère presque comme P2, mais il est toujours environ 14 % plus lent à N égal.**

## 3. Explication

### 3.1 Pourquoi P10 est plus lent : les données passent deux fois par le noyau

- En P2, chaque worker lit son bloc **directement** dans le fichier (le cache du noyau) : une seule copie,
  du cache vers sa mémoire.
- En P10, chaque octet est **lu** par le producteur, **écrit** dans le tube de la file (copie vers le noyau),
  puis **lu** depuis le tube par un consommateur (copie vers sa mémoire). 1,86 Go font ce trajet en plus.
- Cela se voit dans le temps **sys** (temps passé dans le noyau, pour le compte du programme) : environ **3 s**
  en P10 quel que soit N, contre 0,5 s en P2 à N = 1. À N = 1, P10 coûte 3,1 s de CPU de plus que P2,
  dont 2,7 s de sys.
- **Ce surcoût ne dépend pas de N** (le volume copié est toujours le fichier entier) : d'où un rapport P10 ÷ P2
  presque constant (x1,12 à x1,15).

### 3.2 Pourquoi l'écart ne grandit pas avec N : le producteur n'est pas encore le goulot

- Un seul producteur pour N consommateurs : s'il ne lisait pas assez vite, les consommateurs attendraient des lots
  et P10 cesserait d'accélérer. Ce n'est pas le cas jusqu'à N = 8 : l'accélération continue (x3,01 → x4,34)
  et le rapport P10 ÷ P2 reste stable.
- À N = 8, le producteur doit fournir 1,86 Go en 3,3 s, soit environ **570 Mo/s**. Le fichier étant dans le cache
  du noyau, lire et écrire dans un tube est bien plus rapide que l'analyse Python des lignes.
- À N = 1, 1,05 cœur occupé : le producteur ne prend qu'environ 1 s de CPU sur 17 s (estimation : 18,1 s de CPU
  − au plus 17,2 s pour le consommateur). Il travaille **en même temps** que le consommateur (effet de chaîne de
  production), mais c'est le consommateur, plus chargé qu'en P2 (lecture du tube), qui fixe le temps.
- **Hypothèse non mesurée :** avec beaucoup plus de consommateurs, ou un disque lent (fichier pas en cache),
  le producteur deviendrait la limite : c'est la **partie non parallélisable** (loi d'Amdahl, P7) propre à P10.

### 3.3 Cœurs occupés à N = 8 : 6,82 contre 7,21

Il y a 9 processus actifs (8 consommateurs + le producteur), mais les consommateurs passent un peu de temps à
attendre un lot (`get()` sur une file momentanément vide), ou à lire le tube. Le parallélisme utile est donc
un peu plus faible qu'en P2, où chaque worker ne dépend de personne.

## 4. Quand le producteur / consommateur serait-il le meilleur choix ?

P2 gagne ici parce que le journal est un **fichier ordinaire, sur disque** : on connaît sa taille et on peut
sauter n'importe où (`seek`). P10 reste utile quand ce n'est pas le cas :

- **Flux sans `seek`** : journal lu depuis l'entrée standard (`cat access.log | …`), `tail -f` en direct, réseau,
  fichier compressé (`.gz`) : on ne peut pas découper en N blocs à l'avance, mais un producteur peut lire au fil
  de l'eau.
- **Mémoire bornée** garantie par la file (2N lots), quel que soit le volume.
- **Équilibrage automatique** : un consommateur plus rapide prend plus de lots. En P2, les blocs sont fixés au départ ;
  si un bloc était plus coûteux (lignes plus longues, cœur plus lent comme les cœurs « efficaces » de cette puce),
  tous les autres attendraient le dernier worker.

## 5. Lien avec P4 / P5 (section critique et interblocage)

- **Ici il y a une donnée partagée : la file.** Le producteur et les N consommateurs y écrivent et en retirent
  des lots en même temps. C'est une section critique, mais **protégée par `Queue` elle-même** : un verrou pour
  les lectures (un seul consommateur lit le tube à la fois), un verrou pour les écritures, et un **sémaphore
  initialisé à 2N** qui compte les places libres (`put()` le prend, et attend s'il est à 0 ; `get()` le rend).
  C'est le schéma classique du producteur / consommateur vu en cours. Notre code n'ajoute aucun verrou.
  (Vérifié dans `multiprocessing/queues.py` : `_rlock`, `_wlock`, `BoundedSemaphore(maxsize)`.)
- `put()` ne copie pas lui-même le lot dans le tube : il le dépose dans un tampon, et un **thread interne** de la
  file (le *feeder*) le sérialise et l'écrit. Un processus attend que ce thread ait tout écrit avant de se terminer :
  c'est l'origine du piège de `join()` ci-dessous.
- Chaque consommateur garde ses propres `Counter` : comme en P2, la fusion est faite par le seul principal.
- **Attentes sans fin possibles (et comment on les évite) :**

| Situation | Conséquence | Dans notre code |
| --- | --- | --- |
| Oublier un marqueur de fin `None` | un consommateur attend un lot pour toujours (`get()`) | un `None` par consommateur |
| `join()` avant de lire les résultats | un consommateur ne peut pas se terminer tant que son résultat n'est pas lu dans le tube : le principal attend le consommateur, qui attend le principal = **cycle d'attente** (interblocage, Coffman 4) | résultats lus **avant** `join()` (piège signalé par la documentation de `multiprocessing`) |
| Fichier absent | des consommateurs déjà lancés attendraient des lots qui n'arrivent jamais | fichier ouvert **avant** de créer les consommateurs |
| Consommateur tué (`kill -9`, mémoire) | la file se remplit, `put()` du producteur attend sans fin | **non traité** (même limite que P2, voir P5) |

## 6. Limites

- Une seule machine, fichier dans le cache du noyau : avec un disque lent, la lecture par un seul producteur
  pèserait plus.
- Taille des lots (1 Mo) et de la file (2N) choisies a priori, non optimisées.
- La part du producteur (environ 1 s de CPU) est une estimation tirée des temps CPU, pas une mesure directe.
