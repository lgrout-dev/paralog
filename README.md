# Kit étudiant — Projet ParaLog (CESI, S3)

Ce kit contient tout ce qu'il faut pour démarrer le projet sur votre propre machine (Linux ou Windows avec WSL).

Toutes les commandes ci-dessous se lancent **depuis la racine du dépôt**.

| Dossier | Contenu |
| --- | --- |
| `src/` | Code de l'outil d'analyse (versions séquentielle et parallèle) |
| `scripts/` | Scripts utilitaires du kit |
| `data/` | Journaux à analyser |
| `resultats/` | Sorties et mesures de performance |
| `docs/` | Documentation du projet |
| `archives/` | Anciennes versions, livrables archivés |

| Fichier | Rôle |
| --- | --- |
| `scripts/verifier_environnement.sh` | Vérifie que votre machine a bash, Python 3.8+, Git, les commandes du cours, assez de cœurs et d'espace disque |
| `scripts/generer_logs.py` | Génère le journal du projet (`data/access.log`, environ 2 Go) |
| `data/echantillon_access.log` | Extrait de 100 000 lignes (environ 20 Mo) pour développer et tester vite |

## 1. Vérifier votre machine (5 minutes)

```bash
bash scripts/verifier_environnement.sh
```

Corrigez chaque ligne `[KO]` avant le premier jour de réalisation. Sous WSL / Ubuntu : `sudo apt install python3 git`.

## 2. Générer le journal du projet (moins de 2 minutes)

```bash
python3 scripts/generer_logs.py -o data/access.log
```

Le script crée `data/access.log` (9 000 000 de lignes, environ 1,9 Go). **Toutes les équipes obtiennent exactement le même fichier** : la génération est reproductible. Ne modifiez pas la graine, sinon vos résultats ne pourront pas être comparés à ceux attendus.

Ne déposez **jamais** ce fichier sur Git : il est déjà exclu par le `.gitignore` du dépôt. N'oubliez pas l'option `-o data/access.log` : sans elle, le fichier est créé dans le dossier courant.

## 3. Le format d'une ligne

```
10.42.213.80 - - [07/Oct/2026:14:05:32 +0200] "GET /produits/118 HTTP/1.1" 200 45504 "https://www.google.fr/" "Mozilla/5.0 (...)"
```

Champs utiles, numérotés comme pour `cut -d' ' -fN` :

| N° | Contenu | Exemple |
| --- | --- | --- |
| 1 | Adresse IP du client | `10.42.213.80` |
| 4 | Date et heure (l'heure est entre le 1er et le 2e `:`) | `[07/Oct/2026:14:05:32` |
| 6 | Méthode HTTP (avec un guillemet devant) | `"GET` |
| 7 | Page demandée | `/produits/118` |
| 9 | Code de réponse HTTP | `200` |
| 10 | Taille de la réponse en octets (`-` si vide) | `45504` |

## 4. Ce que votre outil doit produire

Pour l'ensemble du fichier :

1. le nombre de requêtes par code HTTP ;
2. les 10 adresses IP les plus actives ;
3. les 10 pages les plus demandées ;
4. le nombre de requêtes par heure (de 00h à 23h).

Commencez par l'échantillon : vos résultats sur `data/echantillon_access.log` doivent être identiques entre votre version séquentielle et votre version parallèle. Passez ensuite au fichier complet pour les mesures de performance.

## Conseils

- Mesurez les temps avec `time python3 src/votre_programme.py data/access.log` et répétez chaque mesure 3 fois.
- Attention aux lignes coupées en deux quand vous découpez le fichier en blocs : chaque bloc doit commencer et finir sur une ligne complète.
- Les adresses IP du journal appartiennent à des plages réservées (documentation ou réseaux privés) : elles ne correspondent à aucune personne réelle.
