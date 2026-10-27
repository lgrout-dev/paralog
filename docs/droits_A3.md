# ParaLog — Droits et groupes (A3)

Source pour le dossier d'architecture. Les droits sont posés par `bash scripts/installer.sh` (A2).

## 1. Le groupe de l'équipe

Un groupe Linux `paralog` réunit les membres de l'équipe. Il est créé **une seule fois** par un administrateur :

```bash
sudo groupadd paralog
sudo usermod -aG paralog UTILISATEUR      # pour chaque membre
```

Le membre doit ensuite se reconnecter (les groupes sont lus à la connexion), puis lancer `bash scripts/installer.sh`, qui attribue le projet au groupe (`chgrp`) et pose les droits.

`installer.sh` n'appelle pas `sudo` lui-même : un script qui demande les droits d'administrateur en cours de route est une mauvaise pratique. Si le groupe n'existe pas, il affiche les commandes ci-dessus et pose quand même les droits.

## 2. Tableau des droits

Rappel de la notation octale : chaque chiffre est la somme de **r = 4** (lire), **w = 2** (écrire), **x = 1** (exécuter un fichier, ou entrer dans un dossier), pour le propriétaire, le groupe, puis les autres. Un 4e chiffre devant (ici **2**) est le bit **setgid**.

| Élément | Octal | Symbolique | Justification |
| --- | --- | --- | --- |
| racine `paralog/` | 750 | `rwxr-x---` | L'équipe entre dans le dossier, les autres ne peuvent même pas y entrer : première barrière. |
| `data/` | 750 | `rwxr-x---` | L'équipe lit les journaux, les autres rien. Seul le propriétaire écrit : les données de référence ne changent pas. |
| `data/*.log` | 640 | `rw-r-----` | Lecture pour le groupe. Pas de `x` : ce sont des données, pas des programmes. |
| `src/` | 750 | `rwxr-x---` | Le groupe lit le code. |
| `src/*.py` | 640 | `rw-r-----` | Lus par l'interpréteur (`python3 src/...`), jamais exécutés directement : le `x` est inutile. |
| `scripts/` | 750 | `rwxr-x---` | |
| `scripts/*.sh` | 750 | `rwxr-x---` | L'équipe peut lancer les scripts ; les autres ne peuvent ni les lire ni les lancer. |
| `scripts/*.py` | 640 | `rw-r-----` | Lancés avec `python3`, comme `src/*.py`. |
| `resultats/` | 2770 | `rwxrws---` | Les membres lancent `lancer.sh`, qui y crée des rapports : il faut l'écriture pour le groupe. Le **setgid** fait que chaque nouveau fichier appartient au groupe `paralog` (et non au groupe personnel de son auteur), donc reste lisible par l'équipe. |
| `resultats/*` | 640 | `rw-r-----` | L'équipe lit les rapports, seul l'auteur les modifie. `lancer.sh` crée ses rapports avec `umask 027`, donc directement en 640. |
| `archives/` | 700 | `rwx------` | Réservé au propriétaire. |
| `archives/*.tar.gz` | 600 | `rw-------` | Réservé au propriétaire. `archiver.sh` les crée avec `umask 077` : jamais lisibles par d'autres, même un instant. |
| `docs/` | 750 | `rwxr-x---` | Le groupe lit la documentation. |
| `docs/*`, `README.md`, `.gitignore` | 640 | `rw-r-----` | Documents : lecture pour le groupe. |

**Aucun droit 777** : `find . -perm -o+w` ne renvoie rien. Le dossier `.git/` n'est pas modifié.

## 3. Preuve (VM Ubuntu, 27/10/2026)

Deux utilisateurs de test : `coequipier` (membre du groupe `paralog`) et `exterieur` (hors groupe).
Le projet est installé dans un dossier commun (copie dans `/tmp/paralog_test`), comme sur un serveur partagé.

| Action | `coequipier` | `exterieur` |
| --- | --- | --- |
| Entrer dans le projet | ✅ | ❌ Permission denied |
| Lire `data/echantillon_access.log` | ✅ | ❌ Permission denied |
| Lancer `bash scripts/lancer.sh ...` | ✅ rapport créé en `640 coequipier:paralog` | ❌ Permission denied (code 126) |
| Écrire dans `data/` | ❌ Permission denied | ❌ |
| Ouvrir `archives/` | ❌ Permission denied | ❌ |

Commandes pour rejouer la preuve (en tant que propriétaire, depuis le dossier commun, après installation) :

```bash
sudo -u coequipier bash scripts/lancer.sh data/echantillon_access.log 2
sudo -u coequipier ls archives
sudo -u exterieur head -n 1 data/echantillon_access.log
sudo -u exterieur bash scripts/lancer.sh data/echantillon_access.log
```

**Remarque :** si le projet est dans un dossier personnel (`/home/louis/paralog`), ce dossier personnel est déjà fermé aux autres (750). Même un membre du groupe ne peut alors pas y entrer. Sur un serveur partagé, on installe le projet dans un dossier commun, par exemple `/srv/paralog`.
