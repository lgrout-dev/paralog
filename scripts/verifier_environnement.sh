#!/bin/bash
# verifier_environnement.sh — Projet ParaLog (CESI, S3)
# Vérifie que votre machine (Linux ou WSL) a tout ce qu'il faut pour le projet et le TP.
# Usage : bash verifier_environnement.sh

ok=0; ko=0
verifier() {  # $1 = libellé, $2 = commande de test
  if eval "$2" >/dev/null 2>&1; then echo "  [OK] $1"; ok=$((ok+1)); else echo "  [KO] $1"; ko=$((ko+1)); fi
}

echo "Vérification de l'environnement ParaLog"
echo "---------------------------------------"
verifier "Shell bash"                         "[ -n \"\$BASH_VERSION\" ]"
for c in grep cut sort uniq wc head tail chmod tar date; do
  verifier "Commande $c"                      "command -v $c"
done
verifier "Python 3.8 ou plus"                 "python3 -c 'import sys; assert sys.version_info >= (3, 8)'"
verifier "Module multiprocessing (Python)"    "python3 -c 'import multiprocessing'"
verifier "Git installé"                       "command -v git"
verifier "Au moins 2 cœurs processeur"        "[ \$(nproc) -ge 2 ]"
verifier "Au moins 5 Go libres dans ~"        "[ \$(df -Pk ~ | awk 'NR==2{print \$4}') -ge 5000000 ]"

echo "---------------------------------------"
echo "Cœurs disponibles : $(nproc)   ·   Espace libre dans ~ : $(df -Ph ~ | awk 'NR==2{print $4}')"
if [ "$ko" -eq 0 ]; then
  echo "Tout est prêt ($ok vérifications réussies)."
else
  echo "$ko point(s) à corriger avant le projet. Sous WSL/Ubuntu : sudo apt install python3 git"
  exit 1
fi
