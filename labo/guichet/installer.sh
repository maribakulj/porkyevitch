#!/bin/sh
# Installe le guichet hors de portée de l'agent. À lancer en root : sudo sh installer.sh PYTHON COMPTE
#   PYTHON : interpréteur >= 3.11 que l'agent ne peut pas modifier (appartenant à root ou au compte du guichet)
#   COMPTE : compte Unix du guichet, déjà créé (par exemple « labo »)
# Le script n'écrit pas dans sudoers : il affiche les deux lignes à ajouter avec `visudo`.
set -eu

PYTHON=${1:?interpréteur Python manquant}
COMPTE=${2:?compte du guichet manquant}
LIB=/usr/local/lib/guichet
BIN=/usr/local/bin
ICI=$(cd "$(dirname "$0")" && pwd)

[ "$(id -u)" = 0 ] || { echo "à lancer en root (sudo)"; exit 1; }
id "$COMPTE" >/dev/null 2>&1 || { echo "compte $COMPTE introuvable : crée-le d'abord"; exit 1; }
UID_GUICHET=$(id -u "$COMPTE")

# L'interpréteur, sa bibliothèque standard et son préfixe ne doivent être modifiables ni par l'agent ni par un groupe :
# un fichier de la stdlib réécrit par l'agent s'exécuterait avec les identifiants du guichet.
"$PYTHON" -I - "$UID_GUICHET" <<'EOF'
import os, stat, sys, sysconfig
if sys.version_info < (3, 11):
    sys.exit(f"Python {sys.version.split()[0]} : il faut 3.11 ou plus (tomllib)")
permis = {0, int(sys.argv[1])}
for chemin in {os.path.realpath(sys.executable), sysconfig.get_paths()["stdlib"], sys.prefix}:
    while True:
        st = os.stat(chemin)
        if st.st_uid not in permis or st.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            sys.exit(f"{chemin} est modifiable par un autre compte (propriétaire {st.st_uid}, mode {oct(st.st_mode)}) :"
                     " prends un Python installé par root (python.org) ou dans le compte du guichet")
        parent = os.path.dirname(chemin)
        if parent == chemin:
            break
        chemin = parent
print(f"interpréteur vérifié : {sys.executable}")
EOF

rm -rf "$LIB"
mkdir -p "$LIB/guichet"
cp "$ICI"/guichet/*.py "$LIB/guichet/"
cp "$ICI/../puissance.py" "$LIB/guichet/puissance.py"  # la porte de recherche recalcule la puissance
printf '%s\n' "$COMPTE" > "$LIB/compte.txt"
chown -R 0:0 "$LIB"
chmod -R u=rwX,go=rX "$LIB"
for nom in guichet guichet-agent; do
    sed -e "s|@PYTHON@|$PYTHON|" -e "s|@LIB@|$LIB|" "$ICI/bin/$nom" > "$BIN/$nom"
    chown 0:0 "$BIN/$nom"
    chmod 755 "$BIN/$nom"
done

MAISON=$(eval echo "~$COMPTE")
mkdir -p "$MAISON/guichet"
[ -f "$MAISON/guichet/config.toml" ] || cp "$ICI/config.exemple.toml" "$MAISON/guichet/config.toml"
chown -R "$COMPTE" "$MAISON/guichet"
chmod 700 "$MAISON" "$MAISON/guichet"

cat <<EOF
Installé : $BIN/guichet-agent et $BIN/guichet, code dans $LIB (root), registre dans $MAISON/guichet.
Ajoute avec \`sudo visudo -f /etc/sudoers.d/guichet\`, en remplaçant AGENT par ton compte :

AGENT ALL=($COMPTE) NOPASSWD: $BIN/guichet-agent
Defaults!$BIN/guichet timestamp_timeout=0

La première ligne laisse l'agent soumettre sans mot de passe ; il n'a que cette commande sous $COMPTE.
La seconde fait demander ton mot de passe à CHAQUE \`sudo -u $COMPTE guichet …\` (approuver, refuser, trancher).
EOF
