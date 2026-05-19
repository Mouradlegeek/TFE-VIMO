#!/bin/bash
# ============================================================
# Script : Recompiler PX4 v1.15 avec BLHeli passthrough
# Auteur : Claude Code — session 19/05/2026
# Usage  : bash build_px4_blheli.sh
# Résultat : build/px4_fmu-v6c_default/px4_fmu-v6c_default.px4
# ============================================================

set -e
BOARD="px4_fmu-v6c"
PX4_VERSION="v1.15.0"
PX4_DIR="$HOME/PX4-Autopilot"

echo "======================================================"
echo " Build PX4 $PX4_VERSION + BLHeli pour $BOARD"
echo "======================================================"

# --- 1. Cloner PX4 si pas déjà présent ---
if [ ! -d "$PX4_DIR" ]; then
    echo "[1/5] Clonage PX4 $PX4_VERSION..."
    git clone https://github.com/PX4/PX4-Autopilot.git \
        --branch $PX4_VERSION --recursive "$PX4_DIR"
else
    echo "[1/5] PX4 déjà cloné dans $PX4_DIR"
    cd "$PX4_DIR"
    git checkout $PX4_VERSION
    git submodule update --init --recursive
fi

cd "$PX4_DIR"

# --- 2. Activer CONFIG_DRIVERS_BLHELI dans le board config ---
BOARD_FILE="boards/px4/fmu-v6c/default.px4board"
echo "[2/5] Ajout CONFIG_DRIVERS_BLHELI=y dans $BOARD_FILE..."

if grep -q "CONFIG_DRIVERS_BLHELI" "$BOARD_FILE"; then
    # Déjà présent — s'assurer qu'il est à y
    sed -i 's/CONFIG_DRIVERS_BLHELI=.*/CONFIG_DRIVERS_BLHELI=y/' "$BOARD_FILE"
    echo "      → Déjà présent, mis à y"
else
    # Ajouter après la ligne CONFIG_DRIVERS_DSHOT si elle existe
    if grep -q "CONFIG_DRIVERS_DSHOT" "$BOARD_FILE"; then
        sed -i '/CONFIG_DRIVERS_DSHOT/a CONFIG_DRIVERS_BLHELI=y' "$BOARD_FILE"
        echo "      → Ajouté après CONFIG_DRIVERS_DSHOT"
    else
        echo "CONFIG_DRIVERS_BLHELI=y" >> "$BOARD_FILE"
        echo "      → Ajouté à la fin du fichier"
    fi
fi

# Vérification
echo "      Contenu autour de BLHeli :"
grep -A1 -B1 "BLHELI" "$BOARD_FILE" || echo "      (non trouvé — vérifier manuellement)"

# --- 3. Installer dépendances si nécessaire ---
echo "[3/5] Vérification des outils de build..."
if ! command -v arm-none-eabi-gcc &> /dev/null; then
    echo "      Installation arm-none-eabi-gcc..."
    sudo apt-get install -y gcc-arm-none-eabi
fi

# --- 4. Compiler ---
echo "[4/5] Compilation pour $BOARD (peut prendre 10-20 min)..."
make ${BOARD}_default -j$(nproc)

# --- 5. Résultat ---
FIRMWARE="build/${BOARD}_default/${BOARD}_default.px4"
if [ -f "$FIRMWARE" ]; then
    echo ""
    echo "======================================================"
    echo " SUCCÈS ! Firmware prêt :"
    echo " $PX4_DIR/$FIRMWARE"
    echo "======================================================"
    echo ""
    echo "PROCHAINE ÉTAPE :"
    echo "  1. Copier ce fichier .px4 sur Windows (clé USB ou réseau)"
    echo "  2. Ouvrir QGroundControl sur Windows"
    echo "  3. Vehicle Setup → Firmware → Custom firmware file"
    echo "  4. Sélectionner ${BOARD}_default.px4"
    echo "  5. Après flash : vérifier dans NSH que 'blheli' répond"
    echo "  6. BLHeliSuite32 → COM3 → Connect → Read Setup"
    echo "     → Activer Bidirectional DShot = ON sur les 4 ESC"
    echo "     → Write Setup"
    echo ""
    echo "PARAMÈTRES PX4 à vérifier dans QGC après flash :"
    echo "  DSHOT_BIDIR_EN  = 1"
    echo "  DSHOT_CONFIG    = 600"
    echo "  MOT_POLE_COUNT  = 14"
    echo "  CBRK_IO_SAFETY  = 22027"
else
    echo "ERREUR : Firmware non trouvé à $FIRMWARE"
    echo "Vérifier les erreurs de compilation ci-dessus."
    exit 1
fi
