# Contexte complet pour Claude — Session Ubuntu

> **Instructions pour Claude :** Lis ce fichier entièrement avant de faire quoi que ce soit.
> Il contient tout le contexte de la session Windows du 19/05/2026 et ce qu'il reste à faire.

---

## Qui est l'utilisateur

**Mourad AARAB**, étudiant ingénieur à l'ISIB (Bruxelles).
Projet TFE : **VIMO** — Visual-Inertial-Motor-based Odometry pour drone GPS-denied.
Pipeline ROS2 100% fonctionnel sur Ubuntu. Dernière étape bloquée : activer **Bidirectional DShot** sur les ESC.

---

## Hardware du drone

| Composant | Détail |
|---|---|
| Châssis | Holybro X500 V6 |
| FC | Holybro Pix32 v6C — STM32H743 — PX4 v1.15 |
| ESC | Flycolor X-Cross HV3 4-en-1 — firmware BLHeli32 |
| Moteurs | Holybro 2216 KV920 — **14 pôles magnétiques** |
| Protocole | DShot600 |
| Batterie | LiPo 4S 5200 mAh XT60 |

---

## Ce qui a été fait sur Windows (session 19/05/2026)

### Objectif initial
Activer **Bidirectional DShot = ON** sur les 4 ESC BLHeli32 via BLHeliSuite32 sur Windows.

### Étapes tentées et résultats

1. **BLHeliSuite32 v32.10** installé → `C:\Users\aarab\Desktop\BLHeliSuite32\BLHeliSuite32.exe`
2. **Connexion FC via USB-C** → COM3 détecté (VID_3185&PID_0038)
3. **Interface** : "SiLabs BLHeli32 Bootloader (Betaflight / Cleanflight)"
4. **Résultat** : Erreur répétée — `Connection to Flightcontroller failed!`

### Cause racine identifiée

**Le firmware PX4 standard pour `px4_fmu-v6c` ne contient pas le module `blheli`.**

Confirmé dans la console NSH via QGC → MAVLink Console :
```
nsh> blheli
nsh: blheli: command not found
```

Liste des builtin apps vérifiée — `blheli` absent, `dshot` présent mais sans passthrough.

Le module `dshot` ne propose pas de commande passthrough :
```
dshot {start|telemetry|reverse|normal|save|3d_on|3d_off|beep1-5|esc_info|stop|status}
```

### Pourquoi USB passthrough ne fonctionne pas avec PX4

BLHeliSuite32 utilise le protocole MSP (Betaflight) pour demander le passthrough au FC.
PX4 n'implémente pas ce protocole sur l'USB — il expose MAVLink uniquement.
Le module `blheli` de PX4 (quand compilé) gère ce passthrough, mais il est absent du build standard.

### Paramètres PX4 actuels (vérifiés/restaurés)

| Paramètre | Valeur | Statut |
|---|---|---|
| `DSHOT_BIDIR_EN` | 1 | Restauré via MAVLink le 19/05/2026 |
| `DSHOT_CONFIG` | 600 | Vérifié |
| `MOT_POLE_COUNT` | 14 | Inchangé |
| `CBRK_IO_SAFETY` | 22027 | Inchangé |

> **Note** : Pendant la session, une tentative de mettre `DSHOT_BIDIR_EN=0` a été faite via MAVLink.
> Il a ensuite été restauré à 1. Vérifier dans QGC avant de flasher.

### Logiciels installés sur Windows

- **BLHeliSuite32 v32.10** : `C:\Users\aarab\Desktop\BLHeliSuite32\BLHeliSuite32.exe`
- **QGroundControl v5.0.8** : installé (chemin exact inconnu, chercher via Win+S "QGroundControl")
- **Port drone** : COM3 (Pix32 v6C USB-C)

---

## Ce qu'il faut faire sur Ubuntu

### Objectif
Recompiler PX4 v1.15 pour `px4_fmu-v6c` en ajoutant `CONFIG_DRIVERS_BLHELI=y`,
puis flasher le firmware custom sur le Pix32 v6C via QGC sur Windows.

### Script disponible

Le script de build est dans ce repo :
```bash
# Télécharger et lancer directement
curl -O https://raw.githubusercontent.com/Mouradlegeek/TFE-VIMO/master/blheli32_windows_guide/build_px4_blheli.sh
bash build_px4_blheli.sh
```

### Ce que fait le script (`build_px4_blheli.sh`)

1. Clone PX4-Autopilot v1.15.0 dans `~/PX4-Autopilot` (si pas déjà présent)
2. Ajoute `CONFIG_DRIVERS_BLHELI=y` dans `boards/px4/fmu-v6c/default.px4board`
3. Compile avec `make px4_fmu-v6c_default`
4. Affiche le chemin du firmware `.px4` généré

### Modifications manuelles si le script échoue

```bash
cd ~/PX4-Autopilot
nano boards/px4/fmu-v6c/default.px4board
# Ajouter la ligne : CONFIG_DRIVERS_BLHELI=y
# Sauvegarder (Ctrl+O, Ctrl+X)
make px4_fmu-v6c_default -j$(nproc)
```

### Résultat attendu

```
build/px4_fmu-v6c_default/px4_fmu-v6c_default.px4
```

---

## Étapes complètes après le build Ubuntu

### 1. Transférer le firmware sur Windows
```bash
# Option clé USB
cp ~/PX4-Autopilot/build/px4_fmu-v6c_default/px4_fmu-v6c_default.px4 /media/mourad/USB/

# Option réseau (si PC Windows sur même réseau)
scp ~/PX4-Autopilot/build/px4_fmu-v6c_default/px4_fmu-v6c_default.px4 mourad@192.168.x.x:~/Desktop/
```

### 2. Flasher sur Windows via QGC

1. Ouvrir QGroundControl sur Windows
2. Brancher Pix32 v6C en USB-C
3. **Vehicle Setup → Firmware**
4. Cocher **"Advanced settings"** → **"Custom firmware file"**
5. Sélectionner `px4_fmu-v6c_default.px4`
6. Cliquer **OK** — attendre ~2 min

### 3. Vérifier que blheli est présent (QGC → MAVLink Console)
```
nsh> blheli
# Doit afficher : Usage: blheli <command> [arguments...]
# et NON "command not found"
```

### 4. Configurer les ESC via BLHeliSuite32

**Prérequis** : Hélices retirées + batterie LiPo branchée + USB-C branché

1. Ouvrir `C:\Users\aarab\Desktop\BLHeliSuite32\BLHeliSuite32.exe`
2. **Select BLHeli_32 Interface** → `SiLabs BLHeli32 Bootloader (Betaflight / Cleanflight)`
3. Port : **COM3**, Baud : **115200**
4. **Connect** → **Read Setup**
5. Pour **chaque ESC** (4 au total) :

| Paramètre | Valeur |
|---|---|
| **Bidirectional DShot** | **ON** ← le plus important |
| Motor Timing | Medium-High (23.4°) |
| PWM Frequency | 48 kHz |
| Temperature Protection | 130°C |
| Beacon Delay | Infinite |

6. **Write Setup** → **Read Setup** (vérifier que Bidirectional = ON sur les 4)

### 5. Vérifier paramètres PX4 dans QGC

S'assurer que ces paramètres sont corrects APRÈS le flash :
- `DSHOT_BIDIR_EN` = **1**
- `DSHOT_CONFIG` = **600**
- `MOT_POLE_COUNT` = **14**
- `CBRK_IO_SAFETY` = **22027**

### 6. Vérification finale sur Ubuntu

```bash
ros2 launch mavros mavros.launch.py fcu_url:=/dev/ttyACM0:921600

# Dans un autre terminal
ros2 topic echo /mavros/esc_status
```

**Résultat attendu** : RPM non-zéro quand les moteurs tournent.
Le noeud `rpm_bridge_node` doit afficher `[DShot Bidir]` au lieu de `[Fallback sqrt]`.

---

## Résumé en une ligne

> Compiler PX4 avec BLHeli → flasher → BLHeliSuite32 active Bidirectional DShot → VIMO reçoit RPM réels.
