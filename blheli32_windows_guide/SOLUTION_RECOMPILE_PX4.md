# Solution : Recompiler PX4 avec BLHeli Passthrough

## Contexte — Pourquoi recompiler ?

Le firmware PX4 v1.15 standard pour le Pix32 v6C (`px4_fmu-v6c`) **ne contient pas le module `blheli`**.
Ce module est indispensable pour que BLHeliSuite32 puisse communiquer avec les ESC via le port USB du FC.

**Confirmation NSH (testée le 19/05/2026) :**
```
nsh> blheli
nsh: blheli: command not found
```

**Ce que cette solution fait :**
- Ajouter `CONFIG_DRIVERS_BLHELI=y` dans le board config
- Recompiler pour `px4_fmu-v6c`
- Flasher le firmware custom sur le Pix32 v6C
- BLHeliSuite32 peut ensuite configurer les ESC via USB

---

## Prérequis (Ubuntu — environnement TFE déjà en place)

```bash
# Vérifier que l'environnement PX4 est présent
cd ~/PX4-Autopilot   # ou le chemin de ton clone PX4
git status
```

Si PX4 n'est pas cloné :
```bash
git clone https://github.com/PX4/PX4-Autopilot.git --branch v1.15.0 --recursive
cd PX4-Autopilot
bash Tools/setup/ubuntu.sh
```

---

## Étapes exactes

### 1. Activer le module BLHeli dans le board config

```bash
cd ~/PX4-Autopilot

# Ouvrir le fichier de config du fmu-v6c
nano boards/px4/fmu-v6c/default.px4board
```

Chercher la section des drivers. Ajouter cette ligne :
```
CONFIG_DRIVERS_BLHELI=y
```

Ou utiliser l'outil menuconfig :
```bash
make px4_fmu-v6c boardconfig
```
Dans l'interface : Drivers → ESC → Enable BLHeli passthrough

### 2. Recompiler

```bash
make px4_fmu-v6c
```

Le firmware compilé se trouve dans :
```
build/px4_fmu-v6c_default/px4_fmu-v6c_default.px4
```

### 3. Flasher via QGroundControl

1. Ouvrir QGroundControl sur **Windows** (le PC connecté au drone)
2. Brancher le Pix32 v6C en USB-C
3. Aller dans : **Vehicle Setup → Firmware**
4. Cocher **"Advanced settings"** → **"Custom firmware file"**
5. Sélectionner `px4_fmu-v6c_default.px4`
6. Cliquer **OK** — le flash prend ~2 min

### 4. Vérifier que blheli est présent

Après le flash, dans QGC → Analyze → MAVLink Console :
```
blheli
```
Doit afficher : `Usage: blheli <command> [arguments...]`

---

## Configurer les ESC via BLHeliSuite32 (après recompilation)

### Matériel
- Pix32 v6C branché en USB-C (COM3)
- Batterie LiPo 4S branchée (ESC alimentés)
- Hélices RETIRÉES

### Logiciel
BLHeliSuite32 v32.10 sur le Bureau Windows (`C:\Users\aarab\Desktop\BLHeliSuite32\`)

### Étapes BLHeliSuite32

1. Lancer `BLHeliSuite32.exe`
2. **Select BLHeli_32 Interface** → `SiLabs BLHeli32 Bootloader (Betaflight / Cleanflight)`
3. Port : **COM3**, Baud : **115200**
4. Cliquer **Connect**
5. Cliquer **Read Setup** → les 4 ESC apparaissent
6. Pour chaque ESC, configurer :

| Paramètre | Valeur |
|---|---|
| **Bidirectional DShot** | **ON** ← CRITIQUE |
| Motor Timing | Medium-High (23.4°) |
| PWM Frequency | 48 kHz |
| Temperature Protection | 130°C |
| Beacon Delay | Infinite |

7. Cliquer **Write Setup**
8. Cliquer **Read Setup** → vérifier que Bidirectional DShot = ON sur les 4 ESC
9. Débrancher la batterie

---

## Paramètres PX4 à vérifier après tout

Dans QGC → Vehicle Setup → Parameters :

| Paramètre | Valeur requise |
|---|---|
| `DSHOT_BIDIR_EN` | **1** |
| `MOT_POLE_COUNT` | **14** |
| `CBRK_IO_SAFETY` | **22027** |
| `DSHOT_CONFIG` | **600** (DShot600) |

Si `DSHOT_BIDIR_EN` est à 0 (j'ai essayé de le modifier le 19/05/2026), le remettre à 1 et rebooter.

---

## Vérification finale (Ubuntu)

```bash
ros2 launch mavros mavros.launch.py fcu_url:=/dev/ttyACM0:921600
ros2 topic echo /mavros/esc_status
```

Les RPM doivent être non-zéro quand les moteurs tournent.
Le noeud `rpm_bridge_node` doit afficher `[DShot Bidir]` au lieu de `[Fallback sqrt]`.

---

## Notes de session (19/05/2026)

- **COM3** = Pix32 v6C sur Windows
- BLHeliSuite32 v32.10 installé dans : `C:\Users\aarab\Desktop\BLHeliSuite32\`
- QGC v5.0.8 installé (chemin inconnu, chercher via Win+Search)
- `DSHOT_BIDIR_EN` a peut-être été mis à 0 par tentative MAVLink → à vérifier et remettre à 1
- ESC : Flycolor X-Cross HV3 4-in-1, firmware BLHeli32
- FC : Holybro Pix32 v6C, PX4 v1.15, STM32H743
